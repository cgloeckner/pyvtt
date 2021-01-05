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
	
