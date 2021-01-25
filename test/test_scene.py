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

class SceneTest(unittest.TestCase):
    
    def setUp(self):
        # create temporary database
        self.db = orm.createGmDatabase(engine=None, filename=':memory:')
        
    def tearDown(self):
        del self.db
        
    @db_session
    def test_preDelete(self):
        demo_game = self.db.Game(url='test', gm_url='foo')
        demo_scene = self.db.Scene(game=demo_game)
        
        # create some tokens
        for i in range(5):
            t = self.db.Token(scene=demo_scene, url='dummy', posx=200, posy=150, size=20)
                        
        # use last token as background
        self.db.commit()
        t.size = -1
        demo_scene.backing = t
        self.assertEqual(t.back, demo_scene)
        
        # prepare scene deletion
        demo_scene.preDelete()
        tokens = self.db.Token.select(lambda t: t.scene == demo_scene)
        self.assertEqual(len(tokens), 0)
        self.assertEqual(demo_scene.backing, None)
        
        # scene can be deleted
        demo_scene.delete()
        self.db.commit()
