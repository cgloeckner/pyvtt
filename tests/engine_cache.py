#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

from pony.orm import db_session

from tests.utils import EngineBaseTest

class EngineCacheTest(EngineBaseTest):
		
	def test_insert(self):     
		cache = self.engine.cache
		
		# @NOTE: first insertion is trigged by postSetup()
		with db_session:
			gm1 = self.engine.main_db.GM(name='foo', url='foo', sid='123')
			gm2 = self.engine.main_db.GM(name='bar', url='bar', sid='456')
			gm1.postSetup()
			gm2.postSetup()
		
		# force 2nd insertion
		with self.assertRaises(KeyError):
			cache.insert(gm1)
		
	def test_get(self):  
		cache = self.engine.cache
		
		with db_session:
			gm1 = self.engine.main_db.GM(name='foo', url='foo', sid='123')
			gm2 = self.engine.main_db.GM(name='bar', url='bar', sid='456')
			gm1.postSetup()
			gm2.postSetup()
		
		# different GMs have different cache instances
		gm1_cache = cache.get(gm1)
		gm2_cache = cache.get(gm2)
		self.assertNotEqual(gm1_cache, gm2_cache)
		
	def getFromUrl(self):   
		cache = self.engine.cache
		
		with db_session:
			gm1 = self.engine.main_db.GM(name='foo', url='foo', sid='123')
			gm2 = self.engine.main_db.GM(name='bar', url='bar', sid='456')
			gm1.postSetup()
			gm2.postSetup()
		
		# different GMs have different cache instances
		gm1_cache = cache.getFromUrl(gm1.url)
		gm2_cache = cache.getFromUrl(gm2.url)
		self.assertNotEqual(gm1_cache, gm2_cache)
		
		# not failing but returns None for unknown GM
		unknown_cache = cache.getFromUrl('some-random-bullshit')
		self.assertIsNone(unknown_cache)
		
	def test_remove(self):  
		cache = self.engine.cache
		
		with db_session:
			gm1 = self.engine.main_db.GM(name='foo', url='foo', sid='123')
			gm2 = self.engine.main_db.GM(name='bar', url='bar', sid='456')
			gm1.postSetup()
			gm2.postSetup()
		
		cache.remove(gm1)
		
		# cannot query removed gm
		unknown_cache = cache.get(gm1)
		self.assertIsNone(unknown_cache)
		
		# cannot delete twice
		with self.assertRaises(KeyError):
			cache.remove(gm1)
		
		# cannot delete unknown GM
		class DummyGm(object):
			def __init__(self, url):
				self.url = url
		dummy_gm = DummyGm('more-crap')
		with self.assertRaises(KeyError):
			cache.remove(dummy_gm)
			
		# can re-insert gm
		gm_cache = cache.insert(gm1)
		self.assertIsNotNone(gm_cache)
		
	def test_listen(self):
		print('\nEngineCache.listen() is not tested')
