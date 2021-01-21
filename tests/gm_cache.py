#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

from pony.orm import db_session

import cache, orm

from tests.utils import EngineBaseTest

class GmCacheTest(EngineBaseTest):
		
	def setUp(self):
		super().setUp()
		
		with db_session:
			gm = self.engine.main_db.GM(name='user123', url='foo', sid='123456')
			gm.postSetup()
			self.cache = self.engine.cache.get(gm)
		
		# create GM database
		self.db = orm.createGmDatabase(engine=self.engine, filename=':memory:')
		
	def test_insert(self):
		# @NOTE: first insertion was trigged by postSetup()
		with db_session:
			game1 = self.db.Game(url='bar', gm_url='foo')
			game2 = self.db.Game(url='lol', gm_url='foo')
			game1.postSetup()
			game2.postSetup()
		
		# force 2nd insertion
		with self.assertRaises(KeyError):
			self.cache.insert(game1)
		
	def test_get(self):  
		with db_session:
			game1 = self.db.Game(url='bar', gm_url='foo')
			game2 = self.db.Game(url='lol', gm_url='foo')
			game1.postSetup()
			game2.postSetup()
		
		# different games have different cache instances
		game1_cache = self.cache.get(game1)
		game2_cache = self.cache.get(game2)
		self.assertNotEqual(game1_cache, game2_cache)
		
	def getFromUrl(self):
		with db_session:
			game1 = self.db.Game(url='bar', gm_url='foo')
			game2 = self.db.Game(url='lol', gm_url='foo')
			game1.postSetup()
			game2.postSetup()
		
		# different games have different cache instances
		game1_cache = self.cache.getFromUrl(game1.url)
		game2_cache = self.cache.getFromUrl(game2.url)
		self.assertNotEqual(game1_cache, game2_cache)
		
		# not failing but returns None for unknown game
		unknown_cache = self.cache.getFromUrl('some-random-bullshit')
		self.assertIsNone(unknown_cache)
		
	def test_remove(self):
		with db_session:
			game1 = self.db.Game(url='bar', gm_url='foo')
			game2 = self.db.Game(url='lol', gm_url='foo')
			game1.postSetup()
			game2.postSetup()
		
		self.cache.remove(game1)
		
		# cannot query removed game
		unknown_cache = self.cache.get(game1)
		self.assertIsNone(unknown_cache)
		
		# cannot delete twice
		with self.assertRaises(KeyError):
			self.cache.remove(game1)
		
		# cannot delete unknown game
		class DummyGame(object):
			def __init__(self, url):
				self.url = url
		dummy_gm = DummyGame('more-crap')
		with self.assertRaises(KeyError):
			self.cache.remove(dummy_gm)
		
		# can re-insert game
		game_cache = self.cache.insert(game1)
		self.assertIsNotNone(game_cache)
