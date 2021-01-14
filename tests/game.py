#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import unittest, os, pathlib

from bottle import FileUpload
from pony.orm import db_session

import orm

from tests.utils import EngineTest

class GameTest(EngineTest):
	
	def setUp(self):
		super().setUp()
		
		# finish GM data
		with db_session:
			gm = self.engine.main_db.GM(name='user123', url='url456', sid='123456')
			gm.postSetup()
		
		# create GM database
		self.db = orm.createGmDatabase(engine=self.engine, filename=':memory:')
		
	def tearDown(self):
		del self.db
		
	@db_session
	def test_getUrl(self):
		game = self.db.Game(url='foo', gm_url='url456')
		url  = game.getUrl()
		self.assertEqual(url, 'url456/foo')
		
	# @NOTE: Game.makeMd5s() not tested directly
		
	@db_session
	def test_postSetup(self):
		game = self.db.Game(url='foo', gm_url='url456')
		
		game_path = self.engine.paths.getGamePath(gm=game.gm_url, game=game.url)
		
		# test game setup
		self.assertFalse(os.path.isdir(game_path))
		game.postSetup()
		self.assertTrue(os.path.isdir(game_path))
		
	# @NOTE: Game.getAllImages() not tested directly
		
	@db_session
	def test_getNextId(self):
		game = self.db.Game(url='foo', gm_url='url456')
		game.postSetup()
		
		# starting id
		i = game.getNextId()
		self.assertEqual(i, 0)
		
		i = game.getNextId()
		self.assertEqual(i, 0)
		
		# gap used for next id
		img_path = self.engine.paths.getGamePath(game.gm_url, game.url)
		for i in [0, 1, 2, 3, 4, 6, 7, 8]:
			p = img_path / '{0}.png'.format(i)
			p.touch()
		i = game.getNextId()
		self.assertEqual(i, 5)
		
		# first unused id
		p = img_path / '5.png'
		p.touch()     
		i = game.getNextId()
		self.assertEqual(i, 9)
		
	@db_session
	def test_getImageUrl(self):
		game = self.db.Game(url='foo', gm_url='url456')
		game.postSetup()
		
		url = game.getImageUrl(17)
		self.assertEqual(url, '/token/url456/foo/17.png')
		
	# @NOTE: Game.getFileSize() is not tested directly
		
	@db_session
	def test_upload(self):
		game = self.db.Game(url='foo', gm_url='url456')
		game.postSetup()
		
		# prepare FileUpload (with this file for demoing purpose)
		fupload = FileUpload(open(__file__, 'rb'), 'test.png', __file__)
		
		# test upload result
		old_id = game.getNextId()
		url = game.upload(fupload)
		new_id = game.getNextId()
		self.assertEqual(old_id + 1, new_id)
		self.assertEqual(url, game.getImageUrl(old_id))
		
		# test file exists   
		img_path = self.engine.paths.getGamePath(game.gm_url, game.url)
		p = img_path / '{0}.png'.format(old_id)
		self.assertTrue(os.path.exists(p))
		
		# check md5 being stored
		md5 = self.engine.getMd5(fupload.file)
		checksums = self.engine.checksums[game.getUrl()]
		self.assertIn(md5, checksums)
		
		# try to reupload file: same file used
		old_id = game.getNextId()
		new_url = game.upload(fupload)
		new_id = game.getNextId()
		self.assertEqual(old_id, new_id)
		self.assertEqual(url, new_url)
		
	@db_session
	def test_getAbandonedImages(self):
		game = self.db.Game(url='foo', gm_url='url456')
		game.postSetup()
		
		# create two empty files (to mimic uploaded images)
		img_path = self.engine.paths.getGamePath(game.gm_url, game.url)
		id1 = game.getNextId()
		p1 = img_path / '{0}.png'.format(id1)
		p1.touch()
		id2 = game.getNextId()
		p2 = img_path / '{0}.png'.format(id2)
		p2.touch()
		
		# assoign second file to token
		demo_scene = self.db.Scene(game=game)
		url = game.getImageUrl(id2)
		self.db.Token(scene=demo_scene, url=url, posx=200, posy=150, size=20)
		self.db.commit()
		
		# expect first file to be abandoned
		abandoned = game.getAbandonedImages()
		self.assertIn(str(p1), abandoned)
		self.assertNotIn(str(p2), abandoned)
		
	@db_session
	def test_cleanup(self):
		game = self.db.Game(url='foo', gm_url='url456')
		game.postSetup()
		
		# create two empty files (to mimic uploaded images)
		img_path = self.engine.paths.getGamePath(game.gm_url, game.url)
		id1 = game.getNextId()
		p1 = img_path / '{0}.png'.format(id1)
		p1.touch()
		id2 = game.getNextId()
		p2 = img_path / '{0}.png'.format(id2)
		p2.touch()
		
		# assoign second file to token
		demo_scene = self.db.Scene(game=game)
		url = game.getImageUrl(id2)
		self.db.Token(scene=demo_scene, url=url, posx=200, posy=150, size=20)
		self.db.commit()
		
		# expect unused files to be deleted
		game.cleanup()                      
		self.assertFalse(os.path.exists(p1))
		self.assertTrue(os.path.exists(p2))
		
	@db_session
	def test_preDelete(self):
		game = self.db.Game(url='foo', gm_url='url456')
		game.postSetup()
		
		# create an empty file (to make sure it isn't blocking removing the directory)
		img_path = self.engine.paths.getGamePath(game.gm_url, game.url)
		id1 = game.getNextId()
		p1 = img_path / '{0}.png'.format(id1)
		p1.touch()
		url = game.getImageUrl(id1)
		
		# create two demo scenes with tokens
		scene1 = self.db.Scene(game=game)
		for i in range(7):
			self.db.Token(scene=scene1, url=url, posx=200, posy=150, size=20)
		scene2 = self.db.Scene(game=game)
		for i in range(4):
			self.db.Token(scene=scene2, url=url, posx=200, posy=150, size=20)
		self.db.commit()
		
		# prepare game for deletion
		game.preDelete()
		self.assertFalse(os.path.exists(img_path))
		gm_cache = self.engine.cache.getFromUrl('url456')
		with self.assertRaises(KeyError):
			gm_cache.get(game)
		
		# delete game
		game.delete()
		self.db.commit() 
		
	@db_session
	def test_toZip(self):
		print('orm/Game.toTip() not tested yet')
		# idea: unzip result, parse json and check if all scenes, tokens and their images are there
		
	@db_session
	def test_fromImage(self):
		print('orm/Game.fromImage() not tested yet')
		# idea: test regular upload, assert game and cache existence, assert initial scene and being active, try to screw the url, try to screw the upload
		
	@db_session
	def test_fromZip(self):
		print('orm/Game.fromZip() not tested yet')
		# idea: reimport exported zip and assert game etc (see fromImage), also try to screw the url, try to use a corrupted zip (no or damaged json)
		
