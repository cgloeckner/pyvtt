#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os, sys, hashlib, time, requests, json, re, shutil

import bottle

from orm import db_session, createMainDatabase
from server import VttServer, PatreonApi, EmailApi, PathApi, LoggingApi
from cache import EngineCache


__author__ = "Christian Glöckner"


class Engine(object):         

	def __init__(self, argv=list()):
		self.paths = PathApi(appname='pyvtt')
		
		# setup per-game stuff
		self.checksums = dict()
		self.locks     = dict()
		
		# webserver stuff
		self.host   = '0.0.0.0'
		self.domain = 'localhost'
		self.port   = 8080 
		self.socket = ''
		self.debug  = False
		self.quiet  = False
		self.ssl    = False
		self.shards = []
		
		self.main_db = None
		
		# blacklist for GM names and game URLs
		self.gm_blacklist = ['', 'static', 'token', 'vtt', 'websocket']
		self.url_regex    = '^[A-Za-z0-9_\-.]+$'
		
		self.local_gm   = False
		self.localhost  = False
		self.title      = 'PyVTT'
		self.links      = None
		self.expire     = 3600 * 24 * 30 # default: 30d
		self.login      = dict() # login settings
		self.login_api  = None   # login api instance
		self.notify     = dict() # crash notify settings
		self.notify_api = None   # notify api instance
		
		self.cache      = None   # later engine cache
		
		self.debug     = '--debug' in argv
		self.quiet     = '--quiet' in argv
		self.local_gm  = '--local-gm' in argv
		self.localhost = '--localhost' in argv
		
		if self.localhost:
			assert(not self.local_gm)
		
		self.logging = LoggingApi(
			info_file   = self.paths.getLogPath('info'),
			error_file  = self.paths.getLogPath('error'),
			access_file = self.paths.getLogPath('access')
		)
		
		self.logging.info('Started Modes: debug={0}, quiet={1}, local_gm={2} localhost={3}'.format(self.debug, self.quiet, self.local_gm, self.localhost))
		
		# handle settings
		settings_path = self.paths.getSettingsPath()
		if not os.path.exists(settings_path):
			# create default settings
			settings = {
				'title'  : self.title,
				'links'  : self.links,
				'shards' : self.shards,
				'expire' : self.expire,
				'hosting': {
					'domain' : self.domain,
					'port'   : self.port,
					'socket' : self.socket,
					'ssl'    : self.ssl
				},
				'login'  : self.login,
				'notify' : self.notify
			}
			with open(settings_path, 'w') as h:
				json.dump(settings, h, indent=4)
				self.logging.info('Created default settings file')
		else:
			# load settings
			with open(settings_path, 'r') as h:
				settings = json.load(h)
				self.title   = settings['title']
				self.links   = settings['links']
				self.shards  = settings['shards']
				self.expire  = settings['expire']
				self.domain  = settings['hosting']['domain']
				self.port    = settings['hosting']['port']
				self.socket  = settings['hosting']['socket']
				self.ssl     = settings['hosting']['ssl']
				self.login   = settings['login']
				self.notify  = settings['notify']
			self.logging.info('Settings loaded')
		
		# show argv help
		if '--help' in argv:
			print('Commandline args:')
			print('    --debug       Starts in debug mode.')
			print('    --quiet       Starts in quiet mode.')
			print('    --local-gm    Starts in local-GM-mode.')
			print('    --localhost   Starts in localhost mode.')
			print('')
			print('Debug Mode:     Enables debug level logging.')
			print('Quiet Mode:     Disables verbose outputs.')
			print('Local-GM Mode:  Replaces `localhost` in all created links by the public ip.')
			print('Localhost Mode: Restricts server for being used via localhost only. CANNOT BE USED WITH --local-gm')
			print('')
			print('See {0} for custom settings.'.format(settings_path))
			sys.exit(0)
		
		if self.localhost:
			# overwrite domain and host to localhost
			self.host   = '127.0.0.1'
			self.domain = 'localhost'
			self.logging.info('Overwriting connections to localhost')
		elif self.local_gm or self.domain == '':
			# overwrite domain with public ip
			self.domain = requests.get('https://api.ipify.org').text
			self.logging.info('Overwriting Domain by Public IP: {0}'.format(self.domain))
		
		# load patreon API
		if self.login['type'] == 'patreon':
			protocol = 'https' if self.ssl else 'http'
			host_callback = '{0}://{1}:{2}/vtt/patreon/callback'.format(protocol, self.getDomain(), self.port)
			# create patreon query API
			self.login_api = PatreonApi(host_callback=host_callback, **self.login)
		
		if self.notify['type'] == 'email':
			# create email notify API
			self.notify_api = EmailApi(**self.notify)
		
		# create main database
		self.main_db = createMainDatabase(self)
		
		# setup db_session to all routes
		app = bottle.default_app()
		app.catchall = not self.debug
		app.install(db_session)
		
		# dice roll specific timers
		self.recent_rolls = 30 # rolls within past 30s are recent
		self.latest_rolls = 60 * 10 # rolls within the past 10min are up-to-date
		
		# game cache
		self.cache = EngineCache(self)
		
	def run(self):
		certfile = ''
		keyfile  = ''
		if self.ssl:
			# enable SSL
			ssl_dir = self.paths.getSslDir()
			certfile = ssl_dir / 'cacert.pem'
			keyfile  = ssl_dir / 'privkey.pem'
			assert(os.path.exists(certfile))
			assert(os.path.exists(keyfile))
		
		ssl_args = {'certfile': certfile, 'keyfile': keyfile} if self.ssl else {}
		
		bottle.run(
			host       = self.host,
			port       = self.port,
			debug      = self.debug,
			quiet      = self.quiet,
			server     = VttServer,
			# VttServer-specific
			unixsocket = self.socket,
			# SSL-specific
			**ssl_args
		)
		
	def getDomain(self):
		if self.localhost:
			# because of forced localhost mode
			return 'localhost'
		else:
			# use domain (might be replaced by public ip)
			return self.domain
		
	def verifyUrlSection(self, s):
		return bool(re.match(self.url_regex, s))
		
	def getClientIp(self, request):
		if self.socket != '':
			return request.environ.get('HTTP_X_FORWARDED_FOR')
		else:
			return request.environ.get('REMOTE_ADDR')
		
	@staticmethod
	def getMd5(handle):
		hash_md5 = hashlib.md5()
		offset = handle.tell()
		for chunk in iter(lambda: handle.read(4096), b""):
			hash_md5.update(chunk)
		# rewind after reading
		handle.seek(offset)
		return hash_md5.hexdigest()
		
	def cleanup(self):
		""" Deletes all export games' zip files, unused images and
		outdated dice roll results from all games.
		Inactive games or even GMs are deleted (see engine.expired).
		"""
		now = time.time()
		
		with db_session:
			for gm in self.main_db.GM.select():
				gm_cache = self.cache.get(gm)
				
				# check if GM expired
				if gm.timeid > 0 and gm.timeid + self.expire < now:
					# remove expired GM
					gm.preDelete()
					gm.delete() 
					
				else:
					# cleanup GM's games
					gm.cleanup(gm_cache.db, now)
		
		# remove all exported games' zip files 
		export_path = self.paths.getExportPath()
		num_files = len(os.listdir(export_path))
		if num_files > 0:
			shutil.rmtree(export_path)
			self.paths.ensure(export_path)
			self.logging.info('Removed {0} game ZIPs'.format(num_files))

