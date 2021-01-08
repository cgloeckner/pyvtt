#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os, sys, pathlib, hashlib, time, requests, json, re

import bottle

from orm import db_session, createMainDatabase
from server import VttServer, PatreonApi, EmailApi, LoggingApi
from cache import EngineCache


__author__ = "Christian Glöckner"


class Engine(object):         

	def __init__(self, argv):
		# get preference dir
		p = pathlib.Path.home()
		if sys.platform.startswith('linux'):
			self.data_dir = p / ".local" / "share"
		else:
			raise NotImplementedError('only linux supported yet')
		
		self.data_dir /= 'pyvtt'
		  
		# ensure pyVTT folders exists
		if not os.path.isdir(self.data_dir ):
			os.mkdir(self.data_dir )
		
		ssl_path = self.getSslPath()
		if not os.path.isdir(ssl_path):
			os.mkdir(ssl_path)
		
		gms_path = self.getGmsPath()
		if not os.path.isdir(gms_path):
			os.mkdir(gms_path)
		
		export_path = self.getExportPath()
		if not os.path.isdir(export_path):
			os.mkdir(export_path)
		
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
			info_file   = self.data_dir / 'info.log',
			error_file  = self.data_dir / 'error.log',
			access_file = self.data_dir / 'access.log'
		)
		
		self.logging.info('Started Modes: debug={0}, quiet={1}, local_gm={2} localhost={3}'.format(self.debug, self.quiet, self.local_gm, self.localhost))
		
		# handle settings
		settings_path = self.data_dir / 'settings.json'
		if not os.path.exists(settings_path):
			# create default settings
			settings = {
				'title'  : self.title,
				'links'  : self.links,
				'shards' : self.shards,
				'expire' : self.expire,
				'domain' : self.domain,
				'port'   : self.port,
				'socket' : self.socket,
				'ssl'    : self.ssl,
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
				self.domain  = settings['domain']
				self.port    = settings['port']
				self.socket  = settings['socket']
				self.ssl     = settings['ssl']
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
		
		# game cache
		self.cache = EngineCache(self)
		
	def getSslPath(self):
		return self.data_dir / 'ssl'
		
	def getGmsPath(self):
		return self.data_dir / 'gms'
		
	def getExportPath(self):
		return self.data_dir / 'export'
		
	def run(self):
		certfile = ''
		keyfile  = ''
		if self.ssl:
			# enable SSL
			ssl_dir = self.getSslDir()
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
		# TODO: rewrite, query all games' dbs
		"""
		now = time.time()      
		with db_session:
			for gm in db.GM.select():
				if gm.timeid > 0 and gm.timeid + engine.expire < now:
					# clear expired GM
					gm.clear()
				else:
					# try to cleanup
					gm.cleanup(now)
			
			# finally delete all expired GMs
			# note: idk why but pony's cascade_delete isn't working
			for gm in db.GM.select(lambda g: g.timeid > 0 and g.timeid + self..expire < now):
				for game in db.Game.select(lambda g: g.gm_url == gm.urli):
					for scene in game.scenes:
						for token in scene.tokens:
							token.delete() 
						scene.delete()
					game.delete()
				gm.delete()
		"""
		raise NotImplemented('NEEDS REWRITE')

