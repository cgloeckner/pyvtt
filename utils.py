#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import sys, os, logging, smtplib, pathlib, tempfile, traceback, uuid, random

import bottle
import patreon


__author__ = 'Christian Glöckner'
__licence__ = 'MIT'



# API for providing local harddrive paths
class PathApi(object):
	
	def __init__(self, appname, root=None):
		""" Uses given root or pick standard preference directory. """
		if root is None:
			# get preference dir
			p = pathlib.Path.home()
			if sys.platform.startswith('linux'):
				p = p / ".local" / "share"
			else:
				raise NotImplementedError('only linux supported yet')
			
			self.root = p / appname
		else:
			self.root = pathlib.Path(root) / appname
		
		# make sure paths exists
		self.ensure(self.root)
		self.ensure(self.getExportPath())
		self.ensure(self.getGmsPath())
		self.ensure(self.getFancyUrlPath())
		
	def ensure(self, path):
		if not os.path.isdir(path):
			os.mkdir(path)
		
	# Engine paths
		
	def getStaticPath(self):
		return self.root / 'static'
		
	def getLogPath(self, fname):
		return self.root / '{0}.log'.format(fname)
		
	def getSettingsPath(self):
		return self.root / 'settings.json'
		
	def getMainDatabasePath(self):
		return self.root / 'main.db'
		 
	def getSslPath(self):
		return self.root / 'ssl'
		   
	def getExportPath(self):
		return self.root / 'export'
		
	def getGmsPath(self, gm=None):
		p = self.root / 'gms'
		if gm is not None:
			p /= gm
		return p
		
	def getFancyUrlPath(self, fname=None):
		p = self.root / 'fancyurl'
		if fname is not None:
			p /= '{0}.txt'.format(fname)
		return p
		
	# GM- and Game-relevant paths
		
	def getDatabasePath(self, gm):
		return self.getGmsPath(gm) / 'gm.db'
		
	def getGamePath(self, gm, game):
		return self.getGmsPath(gm) / game
		


# ---------------------------------------------------------------------

# Email API for error notification
class EmailApi(object):
	
	def __init__(self, engine, **data):
		self.host     = data['host']
		self.port     = data['port']
		self.sender   = data['sender']
		self.user     = data['user']
		self.password = data['password']
		self.login()
		
	def login(self):
		self.smtp = smtplib.SMTP('{0}:{1}'.format(self.host, self.port))
		self.smtp.starttls()
		self.smtp.login(self.user, self.password)
		
	def __call__(self, error_id, message):
		# create mail content
		frm = 'From: pyvtt Server <{0}>'.format(self.sender)
		to  = 'To: Developers <{0}>'.format(self.sender)
		sub = 'Subject: Exception Traceback #{0}'.format(error_id)
		plain = '{0}\n{1}\n{2}\n{3}'.format(frm, to, sub, message)
		
		# send email
		try:
			self.smtp.sendmail(self.sender, self.sender, plain)
		except smtplib.SMTPSenderRefused:
			# re-login and re-try
			self.login()
			self.smtp.sendmail(self.sender, self.sender, plain)


# ---------------------------------------------------------------------

class PatreonApi(object):
	
	def __init__(self, host_callback, **data):
		self.callback      = host_callback         # https://example.com/my/callback/path
		self.client_id     = data['client_id']     # ID of Patreon API key
		self.client_secret = data['client_secret'] # Secret of Patreon API key
		self.min_pledge    = data['min_pledge']    # minimum pledge level for access (amount)
		self.whitelist     = data['whitelist']     # whitelist to ignore pledge level
		
	@staticmethod
	def getUserInfo(json_data):
		return {
			'id'       : int(json_data['data']['id']),
			'username' : json_data['data']['attributes']['full_name']
		}
		
	@staticmethod
	def getPledgeTitles(json_data):
		titles = dict()
		
		if 'included' not in json_data:
			return titles
		
		for item in json_data['included']:
			attribs = item['attributes']
			if 'title' in attribs and 'amount_cents' in attribs:
				title  = attribs['title']
				amount = attribs['amount_cents']
				titles[amount] = title
		
		return titles
		
	@staticmethod
	def getUserPledgeAmount(json_data):
		amount = 0
		for r in json_data['data']['relationships']['pledges']['data']:
			if r['type'] == 'pledge':
				# search included stuff for pledge_id
				for item in json_data['included']:
					if item['id'] == r['id']:
						cents = item['attributes']['amount_cents']
						if cents > amount:
							amount = cents
		return amount
		
	def getAuthUrl(self):
		""" Generate patreon-URL to access in order to fetch data. """
		return 'https://www.patreon.com/oauth2/authorize?response_type=code&client_id={0}&redirect_uri={1}'.format(self.client_id, self.callback)
		
	def getApiClient(self, request):
		""" Called after callback was triggered to fetch acccess_token and
		API instance.
		Returns (token, api)
		"""
		oauth_client = patreon.OAuth(self.client_id, self.client_secret)
		tokens = oauth_client.get_tokens(request.query.code, self.callback)
		access_token = tokens['access_token']
		
		return access_token, patreon.API(access_token)
		
	def getSession(self, request):
		""" Query patreon to return required user data and infos.
		This tests the pledge level. """
		token, client = self.getApiClient(request)
		
		user_response = client.fetch_user()
		json_data     = user_response.json_data
		user          = PatreonApi.getUserInfo(json_data)
		result = {
			'sid'     : token,
			'user'    : user,
			'granted' : False
		}
		
		# test whitelist
		if user['id'] in self.whitelist:
			result['granted'] = True
			return result
		
		# test pledge
		amount = PatreonApi.getUserPledgeAmount(json_data)
		if amount >= self.min_pledge:
			return result['granted'] = True
		
		return result


# ---------------------------------------------------------------------

class LoggingApi(object):
	
	def __init__(self, quiet, info_file, error_file, access_file, warning_file):
		self.log_format = logging.Formatter('[%(asctime)s at %(module)s/%(filename)s:%(lineno)d] %(message)s')
		
		# setup info logger
		self.info_filehandler = logging.FileHandler(info_file, mode='a')
		self.info_filehandler.setFormatter(self.log_format)
		
		self.info_stdouthandler = logging.StreamHandler(sys.stdout)
		self.info_stdouthandler.setFormatter(self.log_format)
		
		self.info_logger = logging.getLogger('info_log')
		self.info_logger.setLevel(logging.INFO)
		self.info_logger.addHandler(self.info_filehandler)
		if not quiet:
			self.info_logger.addHandler(self.info_stdouthandler)
		
		# setup error logger
		self.error_filehandler = logging.FileHandler(error_file, mode='a')
		self.error_filehandler.setFormatter(self.log_format)
		
		self.error_logger = logging.getLogger('error_log')   
		self.error_logger.setLevel(logging.ERROR)
		self.error_logger.addHandler(self.error_filehandler)
		
		# setup access logger
		self.access_filehandler = logging.FileHandler(access_file, mode='a')
		self.access_filehandler.setFormatter(self.log_format)
		
		self.access_logger = logging.getLogger('access_log')
		self.access_logger.setLevel(logging.INFO)
		self.access_logger.addHandler(self.access_filehandler)
		
		# setup warning logger
		self.warning_filehandler = logging.FileHandler(warning_file, mode='a')
		self.warning_filehandler.setFormatter(self.log_format)
		
		self.warning_logger = logging.getLogger('warning_log')   
		self.warning_logger.setLevel(logging.WARNING)
		self.warning_logger.addHandler(self.warning_filehandler)
		
		# link logging handles
		self.info    = self.info_logger.info
		self.error   = self.error_logger.error
		self.access  = self.access_logger.info
		self.warning = self.warning_logger.warning
		
		boot = '{0} {1} {0}'.format('=' * 15, 'STARTED')
		self.info(boot)
		self.error(boot)
		self.access(boot)


# ---------------------------------------------------------------------

class ErrorReporter(object):

	def __init__(self, engine):
		self.engine     = engine
		
	def getStacktrace(self):
		# fetch exception traceback
		with tempfile.TemporaryFile(mode='w+') as h:
			traceback.print_exc(file=h)
			h.seek(0) # rewind after writing
			return h.read()
		
	def plugin(self, func):
		def wrapper(*args, **kwargs):
			try:
				return func(*args, **kwargs)
			except bottle.HTTPResponse as e:
				raise
			except (KeyboardInterrupt, SystemExit):
				raise
			except Exception as error:
				# fetch stacktrace and other debugging data
				stacktrace = self.getStacktrace()
				error_id   = uuid.uuid1().hex
				full_url   = bottle.request.fullpath
				client_ip  = self.engine.getClientIp(bottle.request)
				cookies    = ''
				for key in bottle.request.cookies.keys():
					cookies += '\t{0} : {1}\n'.format(key, bottle.request.cookies[key])
				if cookies == '':
					cookies = '{}'
				else:
					cookies = '{\n' + cookies + '}'
				
				message = 'Error ID  = #{0}\nRoute URL = {1}\nClient-IP = {2}\nCookies   = {3}\n\n{4}'.format(
					error_id, full_url, client_ip, cookies, stacktrace)
				
				# log error and notify developer
				self.engine.logging.error(message)
				if self.engine.notify_api is not None:
					self.engine.notify_api(error_id, message)
				
				# notify user about error
				if bottle.request.is_ajax:
					# cause handling in javascript
					bottle.abort(500, error_id)
				else:
					# custom errorpage
					bottle.redirect('/vtt/error/{0}'.format(error_id))
		return wrapper


# ---------------------------------------------------------------------

class FancyUrlApi(object):
	
	def __init__(self, paths):
		self.paths = paths
		self.parts = dict()
		
		# load word lists
		for p in ['verbs', 'adjectives', 'nouns']:
			self.parts[p] = self.load(p)
		
	def load(self, fname):
		# load words
		p = self.paths.getFancyUrlPath(fname)
		with open(p, mode='r') as h:
			content = h.read()
		words = content.split('\n')
		if words[-1] == '':
			# ignore empty line at eof
			words.pop()
		
		# test words not being empty
		for w in words:
			assert(w != '')
			
		return words
		
	@staticmethod
	def pick(src):
		index = random.randrange(0, len(src) - 1)
		return src[index]
		
	def __call__(self):
		""" Generate a random url using <verb>-<adverb>-<noun>.
		"""
		results = []
		for p in self.parts:
			l = self.parts[p]
			w = FancyUrlApi.pick(l)
			results.append(w)
		return '-'.join(results)

