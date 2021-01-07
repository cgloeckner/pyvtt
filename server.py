#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os# , smtplib
import patreon, urllib
import sys, logging

from bottle import request, ServerAdapter

from gevent.pywsgi import WSGIServer
from gevent import socket
from geventwebsocket.handler import WebSocketHandler


__author__ = "Christian Glöckner"


# Server adapter providing support for WebSockets and UnixSocket
class VttServer(ServerAdapter):
	
	def __init__(self, host, port, **options):
		# handle given unixsocket
		self.unixsocket = ''
		if 'unixsocket' in options:
			self.unixsocket = options['unixsocket']
			del options['unixsocket']
		
		# create ServerAdapter
		super().__init__(host, port, **options)
	
	def run(self, handler):
		if self.unixsocket != '':
			# create listener for unix socket
			if os.path.exists(self.unixsocket):
				os.remove(self.unixsocket)
			self.listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
			self.listener.bind(self.unixsocket)
			self.listener.listen(1)   
			print('Listening on unixsocket: {0}'.format(self.unixsocket))
			
			# run server using unix socket
			server = WSGIServer(self.listener, handler, handler_class=WebSocketHandler, **self.options)
			
		else:
			# start server using a regular host-port-configuration
			server = WSGIServer((self.host, self.port), handler, handler_class=WebSocketHandler, **self.options)
		
		# run server
		server.serve_forever()
		


# Email API for sending password reset emails
class EmailApi(object):
	
	def __init__(self, title, host, port, sender, user, password):
		self.title    = title
		self.host     = host
		self.port     = port
		self.sender   = sender
		self.user     = user
		self.password = password
		self.mail_tpl = """From: {0}
To: {1}
Subject: {2}

{3}"""
		self.login()
		
	def login(self):
		self.smtp = smtplib.SMTP('{0}:{1}'.format(self.host, self.port))
		self.smtp.starttls()
		self.smtp.login(self.user, self.password)
		
	def __call__(self, receiver, from_, to, subject, msg):
		plain = 'From: {0}\nTo: {1}\nSubject: {2}\n\n{3}'.format(from_, to, subject, msg)
		try:
			self.smtp.sendmail(self.sender, receiver, plain)
		except smtplib.SMTPSenderRefused:
			# re-login and re-try
			self.login()
			self.smtp.sendmail(self.sender, receiver, plain)
		
	def sendJoinMail(self, receiver, gmname, url):
		from_   = '{0} <{1}>'.format(self.title, self.sender)
		to      = '{0}'.format(receiver)
		subject = 'Welcome'
		msg     = 'Welcome {0},\n\nYour account was linked to your web-browser. In case you delete your cookies, click the link below to reconnect:\n\n{1}.\n\nDo NOT share this link with anybody else.'.format(gmname, url)
		self.__call__(receiver, from_, to, subject, msg)



class PatreonApi(object):
	
	def __init__(self, host_callback, client_id, client_secret, min_pledge, whitelist):
		self.callback      = host_callback # https://example.com/my/callback/path
		self.client_id     = client_id     # ID of Patreon API key
		self.client_secret = client_secret # Secret of Patreon API key
		self.min_pledge    = min_pledge    # minimum pledge level for access (amount)
		self.whitelist     = whitelist     # whitelist to ignore pledge level
		
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
	def getUserPledges(json_data):
		pledges = []  
		titles = PatreonApi.getPledgeTitles(json_data)
		
		for r in json_data['data']['relationships']['pledges']['data']:
			if r['type'] == 'pledge':
				# search included stuff for pledge_id
				for item in json_data['included']:
					if item['id'] == r['id']:
						amount = item['attributes']['amount_cents']
						pledges.append({
							'amount' : amount,
							'title'  : titles[amount]
						})
		
		return pledges
		
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
			'sid'   : token,
			'user'  : user,
			'level' : None # None equals whitelist guest
		}
		
		# test whitelist
		if user['id'] in self.whitelist:
			return result
		
		# test pledge
		pledges = PatreonApi.getUserPledges(json_data)
		for item in pledges:
			if item['amount'] >= self.min_pledge:
				result['level'] = item['title']
				return result
		
		# user neither pledged nor whitelisted
		result['sid'] = None
		return result


class LoggingApi(object):
	
	def __init__(self, info_file, error_file, access_file):
		self.log_format = logging.Formatter('[%(asctime)s at %(module)s/%(filename)s:%(lineno)d] %(message)s')
		
		# setup info logger
		self.info_filehandler = logging.FileHandler(info_file, mode='a')
		self.info_filehandler.setFormatter(self.log_format)
		
		self.info_stdouthandler = logging.StreamHandler(sys.stdout)
		self.info_stdouthandler.setFormatter(self.log_format)
		
		self.info_logger = logging.getLogger('info_log')
		self.info_logger.setLevel(logging.INFO)
		self.info_logger.addHandler(self.info_filehandler)
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
		
		# link logging handles
		self.info   = self.info_logger.info
		self.error  = self.error_logger.error
		self.access = self.access_logger.info
		
		boot = '{0} {1} {0}'.format('=' * 15, 'STARTED')
		self.info(boot)
		self.error(boot)
		self.access(boot)
	
