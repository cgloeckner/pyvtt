#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import unittest, webtest, sys, tempfile, pathlib, bottle

import vtt
from utils import PathApi
from engine import Engine

class EngineTest(unittest.TestCase):
		
	def setUp(self):
		# create temporary directory
		self.tmpdir = tempfile.TemporaryDirectory()
		root        = pathlib.Path(self.tmpdir.name)
		
		# pregenerate paths api for dummyfiles            
		paths = PathApi(appname='unittest', root=root)
		for w in ['verbs', 'adjectives', 'nouns']:
			with open(paths.getFancyUrlPath() / '{0}.txt'.format(w), 'w') as h:
				h.write('demo')
		
		# load engine app into webtest
		self.engine = Engine(argv=['--quiet'], pref_dir=root)
		self.app    = webtest.TestApp(self.engine.app)
		
	def tearDown(self):
		# unload engine
		del self.app
		del self.engine
		del self.tmpdir

