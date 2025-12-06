"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2022 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import unittest
from pony.orm import db_session

from vtt import engine
from vtt import orm


class SceneTest(unittest.TestCase):
    
    def setUp(self):
        # create temporary database
        dummy_engine = engine.Engine()
        self.db = orm.create_gm_database(dummy_engine, filename=':memory:')
        
    def tearDown(self):
        del self.db
        
    @db_session
    def test_preDelete(self):
        demo_game = self.db.Game(url='test', gm_url='foo')
        demo_scene = self.db.Scene(game=demo_game)
        
        # create some tokens
        for i in range(5):
            t = demo_scene.create_token(
                url='dummy', 
                posx=200, 
                posy=150, 
                size=20
            )
                        
        # use last token as background
        self.db.commit()
        t.size = -1
        demo_scene.backing = t
        self.assertEqual(t.back, demo_scene)
        
        # prepare scene deletion
        demo_scene.pre_delete()
        tokens = self.db.Token.select(lambda _t: _t.scene == demo_scene)
        self.assertEqual(len(tokens), 0)
        self.assertEqual(demo_scene.backing, None)
        
        # scene can be deleted
        demo_scene.delete()
        self.db.commit()
