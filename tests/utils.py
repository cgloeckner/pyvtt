#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import unittest, webtest, sys, tempfile, pathlib, bottle

from geventwebsocket.exceptions import WebSocketError

import vtt
from utils import PathApi
from engine import Engine

class EngineBaseTest(unittest.TestCase):
		
	def setUp(self):
		# create temporary directory
		self.tmpdir = tempfile.TemporaryDirectory()
		self.root   = pathlib.Path(self.tmpdir.name)
		
		# pregenerate paths api for dummyfiles            
		paths = PathApi(appname='unittest', root=self.root)
		for w in ['verbs', 'adjectives', 'nouns']:
			with open(paths.getFancyUrlPath() / '{0}.txt'.format(w), 'w') as h:
				h.write('demo')
		
		# load engine app into webtest
		self.engine = Engine(argv=['--quiet'], pref_dir=self.root)
		self.app    = webtest.TestApp(self.engine.app)
		
		self.monkeyPatch()
		
	def monkeyPatch(self):
		# monkey-patch engine
		self.engine.getPublicIp = lambda: '?.?.?.?'
		self.engine.getCountryFromIp = lambda ip: 'unknown'
		
	def tearDown(self):
		# unload engine
		del self.app
		del self.engine
		del self.tmpdir


# ---------------------------------------------------------------------

class SocketDummy(object):
	""" Dummy class for working with a socket.
	"""
	
	def __init__(self):
		self.read_buffer  = list()
		self.write_buffer = list()
		
		self.closed = False
		
	def receive(self):
		if self.closed:
			raise WebSocketError('SocketDummy is closed')
		return self.read_buffer.pop(0)
		
	def send(self, s):
		if self.closed:
			raise WebSocketError('SocketDummy is closed')
		self.write_buffer.append(s)
		
	def close(self):
		if self.closed:
			raise WebSocketError('SocketDummy is closed')
		self.closed = True
