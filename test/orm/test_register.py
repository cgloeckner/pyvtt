"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) Christian Glöckner
License: MIT (see LICENSE for details)
"""

from test.common import EngineBaseTest
from vtt.orm import register


class RegisterTest(EngineBaseTest):

    def test_create_main_database(self):
        # this got called by the engine ctor in EngineBaseTest's setUp

        # check registered classes
        self.assertIn('GM', self.engine.orm)
        self.assertNotIn('Game', self.engine.orm)
        self.assertNotIn('Scene', self.engine.orm)
        self.assertNotIn('Token', self.engine.orm)
        self.assertNotIn('Roll', self.engine.orm)

    def test_gm_database(self):
        path = self.engine.paths.get_database_path('test-gm')
        path.parent.mkdir()
        
        db = register.create_gm_database(self.engine, 'test-gm')

        # assume to be different database
        self.assertNotEqual(db, self.engine.main_db)

        # check registered classes
        self.assertIn('GM', self.engine.orm)
        self.assertIn('Game', self.engine.orm)
        self.assertIn('Scene', self.engine.orm)
        self.assertIn('Token', self.engine.orm)
        self.assertIn('Roll', self.engine.orm)

    def test_create_main_database_in_single_mode(self):
        self.reloadEngine(argv=['--single-db-mode'])
        
        # check registered classes
        self.assertIn('GM', self.engine.orm)
        self.assertIn('Game', self.engine.orm)
        self.assertIn('Scene', self.engine.orm)
        self.assertIn('Token', self.engine.orm)
        self.assertIn('Roll', self.engine.orm)

    def test_create_gm_database_in_single_mode(self):
        self.reloadEngine(argv=['--single-db-mode'])
        
        db = register.create_gm_database(self.engine, 'does-not-matter')
        
        # assume to be same database
        self.assertEqual(db, self.engine.main_db)

        # check registered classes
        self.assertIn('GM', self.engine.orm)
        self.assertIn('Game', self.engine.orm)
        self.assertIn('Scene', self.engine.orm)
        self.assertIn('Token', self.engine.orm)
        self.assertIn('Roll', self.engine.orm)
