#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os, smtplib

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

