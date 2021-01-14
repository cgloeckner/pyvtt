#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import unittest
from pony.orm import db_session

import orm

class TokenTest(unittest.TestCase):
	
	def setUp(self):
		# create temporary database
		self.db = orm.createGmDatabase(engine=None, filename=':memory:')
		
	def tearDown(self):
		del self.db
		
	@db_session
	def test_update(self):
		demo_game  = self.db.Game(url='test', gm_url='foo')
		demo_scene = self.db.Scene(game=demo_game)
		t = self.db.Token(scene=demo_scene, url='dummy', posx=200, posy=150, size=20, zorder=5, rotate=33.4, flipx=True)
		
		# moving token
		t.update(timeid=124, pos=(90, 123))
		self.assertEqual(t.timeid, 124)
		self.assertEqual(t.posx, 90)
		self.assertEqual(t.posy, 123)
		self.assertEqual(t.size, 20)
		self.assertEqual(t.zorder, 5)
		self.assertEqual(t.rotate, 33.4)
		self.assertTrue(t.flipx)
		self.assertFalse(t.locked)
		
		# todo: test moving outside
		
		# resizing token
		t.update(timeid=125, size=39)
		self.assertEqual(t.timeid, 125)
		self.assertEqual(t.posx, 90)
		self.assertEqual(t.posy, 123)
		self.assertEqual(t.size, 39)
		self.assertEqual(t.zorder, 5)
		self.assertEqual(t.rotate, 33.4)
		self.assertTrue(t.flipx)
		self.assertFalse(t.locked)
		
		# layering token
		t.update(timeid=126, zorder=10)
		self.assertEqual(t.timeid, 126)
		self.assertEqual(t.posx, 90)
		self.assertEqual(t.posy, 123)
		self.assertEqual(t.size, 39)
		self.assertEqual(t.zorder, 10)
		self.assertEqual(t.rotate, 33.4)
		self.assertTrue(t.flipx)
		self.assertFalse(t.locked)
		
		# rotating token
		t.update(timeid=127, rotate=90.0)
		self.assertEqual(t.timeid, 127)
		self.assertEqual(t.posx, 90)
		self.assertEqual(t.posy, 123)
		self.assertEqual(t.size, 39)
		self.assertEqual(t.zorder, 10)
		self.assertEqual(t.rotate, 90.0)
		self.assertTrue(t.flipx)
		self.assertFalse(t.locked)
		
		# flipping token
		t.update(timeid=128, flipx=False)
		self.assertEqual(t.timeid, 128)
		self.assertEqual(t.posx, 90)
		self.assertEqual(t.posy, 123)
		self.assertEqual(t.size, 39)
		self.assertEqual(t.zorder, 10)
		self.assertEqual(t.rotate, 90.0)
		self.assertFalse(t.flipx)
		self.assertFalse(t.locked)
		
		# locking token
		t.update(timeid=129, locked=True)
		self.assertEqual(t.timeid, 129)
		self.assertEqual(t.posx, 90)
		self.assertEqual(t.posy, 123)
		self.assertEqual(t.size, 39)
		self.assertEqual(t.zorder, 10)
		self.assertEqual(t.rotate, 90.0)
		self.assertFalse(t.flipx)
		self.assertTrue(t.locked)
		
		# cannot update locked token 
		t.update(timeid=130, pos=(0, 0), size=10, zorder=3, rotate=22.5, flipx=True)
		self.assertEqual(t.timeid, 129)
		self.assertEqual(t.posx, 90)
		self.assertEqual(t.posy, 123)
		self.assertEqual(t.size, 39)
		self.assertEqual(t.zorder, 10)
		self.assertEqual(t.rotate, 90.0)
		self.assertFalse(t.flipx)
		self.assertTrue(t.locked)
		
		# can unlock token update locked token 
		t.update(timeid=131, locked=False)
		self.assertEqual(t.timeid, 131)
		self.assertEqual(t.posx, 90)
		self.assertEqual(t.posy, 123)
		self.assertEqual(t.size, 39)
		self.assertEqual(t.zorder, 10)
		self.assertEqual(t.rotate, 90.0)
		self.assertFalse(t.flipx)
		self.assertFalse(t.locked)
		
	def test_getPosByDegree(self):
		# calc position of three tokens in "circle"
		p = list()
		origin = (100, 100)
		p.append(self.db.Token.getPosByDegree(origin, 0, 3))
		p.append(self.db.Token.getPosByDegree(origin, 1, 3))
		p.append(self.db.Token.getPosByDegree(origin, 2, 3))
		
		self.assertIn(( 51,  72), p) # top left
		self.assertIn((100, 155), p) # right
		self.assertIn((147,  72), p) # bottom left
		
		# calc position of four tokens in "circle"
		p = list()
		p.append(self.db.Token.getPosByDegree(origin, 0, 4))
		p.append(self.db.Token.getPosByDegree(origin, 1, 4))
		p.append(self.db.Token.getPosByDegree(origin, 2, 4))
		p.append(self.db.Token.getPosByDegree(origin, 3, 4))
		
		self.assertIn(( 99,  36), p) # top (99 ~ 100)
		self.assertIn((163,  99), p) # right
		self.assertIn((100, 164), p) # bottom
		self.assertIn(( 36, 100), p) # left
		
		# calc position close to scene's topleft border 
		p = list()          
		origin = (0, 0)
		p.append(self.db.Token.getPosByDegree(origin, 0, 3))
		p.append(self.db.Token.getPosByDegree(origin, 1, 3))
		p.append(self.db.Token.getPosByDegree(origin, 2, 3))
		
		self.assertIn(( 0,  0), p) # top left (limited to scene)
		self.assertIn(( 0, 55), p) # right
		self.assertIn((47,  0), p) # bottom left (limited to scene)
		
		# calc position close to scene's bottomright border 
		p = list()          
		origin = (orm.MAX_SCENE_WIDTH, orm.MAX_SCENE_HEIGHT)
		p.append(self.db.Token.getPosByDegree(origin, 0, 3))
		p.append(self.db.Token.getPosByDegree(origin, 1, 3))
		p.append(self.db.Token.getPosByDegree(origin, 2, 3))
		
		self.assertIn(( 951, 532), p) # top left
		self.assertIn((1000, 560), p) # right (limited to scene)
		self.assertIn((1000, 532), p) # bottom left (limited to scene)
		
		# single token is placed at origin
		origin = (456, 123)
		p = self.db.Token.getPosByDegree(origin, 0, 1)
		self.assertEqual(p, origin)

