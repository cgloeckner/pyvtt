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
        t = self.db.Token(scene=demo_scene, url='dummy', posx=200, posy=150, size=20, zorder=5, rotate=33.4, flipx=True, text='test', color='red')
        
        # moving token
        self.assertTrue(t.update(timeid=100, pos=(90, 123)))
        self.assertEqual(t.timeid, 100)
        self.assertEqual(t.posx, 90)
        self.assertEqual(t.posy, 123)
        self.assertEqual(t.size, 20)
        self.assertEqual(t.zorder, 5)
        self.assertEqual(t.rotate, 33.4)
        self.assertTrue(t.flipx)
        self.assertFalse(t.locked)
        self.assertEqual(t.text, 'test')
        self.assertEqual(t.color, 'red')
        
        # cannot move outside canvas bounds
        self.assertTrue(t.update(timeid=110, pos=(-1, -1)))
        self.assertEqual(t.posx, 0)
        self.assertEqual(t.posy, 0)
        t.update(timeid=111, pos=(orm.MAX_SCENE_WIDTH+1, orm.MAX_SCENE_HEIGHT+1))
        self.assertEqual(t.posx, orm.MAX_SCENE_WIDTH)
        self.assertEqual(t.posy, orm.MAX_SCENE_HEIGHT)
        # move back to regular position
        t.update(timeid=112, pos=(90, 123))
        
        # resizing token
        self.assertTrue(t.update(timeid=113, size=39))
        self.assertEqual(t.timeid, 113)
        self.assertEqual(t.posx, 90)
        self.assertEqual(t.posy, 123)
        self.assertEqual(t.size, 39)
        self.assertEqual(t.zorder, 5)
        self.assertEqual(t.rotate, 33.4)
        self.assertTrue(t.flipx)
        self.assertFalse(t.locked)   
        self.assertEqual(t.text, 'test')
        self.assertEqual(t.color, 'red')
        
        # cannot resize token with too small or too large value
        self.assertTrue(t.update(timeid=114, size=orm.MIN_TOKEN_SIZE-1))
        self.assertEqual(t.size, orm.MIN_TOKEN_SIZE)
        self.assertTrue(t.update(timeid=115, size=orm.MAX_TOKEN_SIZE+1))
        self.assertEqual(t.size, orm.MAX_TOKEN_SIZE)
        self.assertTrue(t.update(timeid=116, size=-1))
        self.assertEqual(t.size, orm.MIN_TOKEN_SIZE)
        # resize back to regular size
        self.assertTrue(t.update(timeid=117, size=39))
        
        # layering token
        self.assertTrue(t.update(timeid=126, zorder=10))
        self.assertEqual(t.timeid, 126)
        self.assertEqual(t.posx, 90)
        self.assertEqual(t.posy, 123)
        self.assertEqual(t.size, 39)
        self.assertEqual(t.zorder, 10)
        self.assertEqual(t.rotate, 33.4)
        self.assertTrue(t.flipx)
        self.assertFalse(t.locked)  
        self.assertEqual(t.text, 'test')
        self.assertEqual(t.color, 'red')
        
        # rotating token
        self.assertTrue(t.update(timeid=127, rotate=90.0))
        self.assertEqual(t.timeid, 127)
        self.assertEqual(t.posx, 90)
        self.assertEqual(t.posy, 123)
        self.assertEqual(t.size, 39)
        self.assertEqual(t.zorder, 10)
        self.assertEqual(t.rotate, 90.0)
        self.assertTrue(t.flipx)
        self.assertFalse(t.locked)
        
        # flipping token
        self.assertTrue(t.update(timeid=128, flipx=False))
        self.assertEqual(t.timeid, 128)
        self.assertEqual(t.posx, 90)
        self.assertEqual(t.posy, 123)
        self.assertEqual(t.size, 39)
        self.assertEqual(t.zorder, 10)
        self.assertEqual(t.rotate, 90.0)
        self.assertFalse(t.flipx)
        self.assertFalse(t.locked)  
        self.assertEqual(t.text, 'test')
        self.assertEqual(t.color, 'red')
        
        # locking token
        self.assertTrue(t.update(timeid=129, locked=True))
        self.assertEqual(t.timeid, 129)
        self.assertEqual(t.posx, 90)
        self.assertEqual(t.posy, 123)
        self.assertEqual(t.size, 39)
        self.assertEqual(t.zorder, 10)
        self.assertEqual(t.rotate, 90.0)
        self.assertFalse(t.flipx)
        self.assertTrue(t.locked) 
        self.assertEqual(t.text, 'test')
        self.assertEqual(t.color, 'red')
        
        # cannot update locked token 
        self.assertFalse(t.update(timeid=130, pos=(0, 0), size=10, zorder=3, rotate=22.5, flipx=True, label=('foobar', 'green')))
        self.assertEqual(t.timeid, 129)
        self.assertEqual(t.posx, 90)
        self.assertEqual(t.posy, 123)
        self.assertEqual(t.size, 39)
        self.assertEqual(t.zorder, 10)
        self.assertEqual(t.rotate, 90.0)
        self.assertFalse(t.flipx)
        self.assertTrue(t.locked) 
        self.assertEqual(t.text, 'test')
        self.assertEqual(t.color, 'red')
        
        # can unlock token update locked token 
        self.assertTrue(t.update(timeid=131, locked=False))
        self.assertEqual(t.timeid, 131)
        self.assertEqual(t.posx, 90)
        self.assertEqual(t.posy, 123)
        self.assertEqual(t.size, 39)
        self.assertEqual(t.zorder, 10)
        self.assertEqual(t.rotate, 90.0)
        self.assertFalse(t.flipx)
        self.assertFalse(t.locked)  
        self.assertEqual(t.text, 'test')
        self.assertEqual(t.color, 'red')

        # can change label with color
        self.assertTrue(t.update(timeid=132, label=('foobar', 'green')))
        self.assertEqual(t.timeid, 132)
        self.assertEqual(t.posx, 90)
        self.assertEqual(t.posy, 123)
        self.assertEqual(t.size, 39)
        self.assertEqual(t.zorder, 10)
        self.assertEqual(t.rotate, 90.0)
        self.assertFalse(t.flipx)
        self.assertFalse(t.locked)  
        self.assertEqual(t.text, 'foobar')
        self.assertEqual(t.color, 'green')

        # update without data does nothing
        self.assertFalse(t.update(timeid=132))
        
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
        
        self.assertIn((959, 539), p) # top left
        self.assertIn((orm.MAX_SCENE_WIDTH, orm.MAX_SCENE_HEIGHT), p) # right (limited to scene)
        self.assertIn((orm.MAX_SCENE_WIDTH, 539), p) # bottom left (limited to scene)
        
        # single token is placed at origin
        origin = (456, 123)
        p = self.db.Token.getPosByDegree(origin, 0, 1)
        self.assertEqual(p, origin)

