#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

from pony.orm import db_session

import cache, orm

from test.utils import EngineBaseTest, SocketDummy

class GameCacheTest(EngineBaseTest):
        
    def setUp(self):
        super().setUp()
        
        with db_session:
            gm = self.engine.main_db.GM(name='user123', url='foo', sid='123456')
            gm.postSetup()
        
        # create GM database
        self.db = orm.createGmDatabase(engine=self.engine, filename=':memory:')
        
        with db_session:
            game = self.db.Game(url='bar', gm_url='foo')
            game.postSetup()
            self.cache = self.engine.cache.get(gm).get(game)
        
    def tearDown(self):
        del self.db
        del self.cache
        
        super().tearDown()
        
    def test_getNextId(self):
        self.assertEqual(self.cache.getNextId(), 0)
        self.assertEqual(self.cache.getNextId(), 1)
        self.assertEqual(self.cache.getNextId(), 2)
        self.assertEqual(self.cache.getNextId(), 3)
        
    def rebuildIndices(self):
        # @NOTE: this is called on insert and remove. hence it's tested
        # during those operations
        pass
        
    def test_insert(self):
        # create some players
        p = self.cache.insert('arthur', 'red', False)
        self.assertIsNotNone(p)
        self.cache.insert('bob', 'blue', True) # GM
        self.cache.insert('carlos', 'yellow', False)
        
        # test indices being rebuilt
        ids = set()
        for name in self.cache.players:
            ids.add(self.cache.players[name].index)
        self.assertEqual(len(ids), 3)
        self.assertEqual(ids, {0, 1, 2})
        
        # force carlos to be online
        self.cache.get('carlos').socket = SocketDummy()
        # cannot add player twice (if online)
        with self.assertRaises(KeyError) as e:
            self.cache.insert('carlos', 'black', True)
            self.assertEqual(str(e), 'carlos')
            
        # can re-login player if offline
        self.cache.insert('bob', 'cyan', False)
        
    def test_get(self): 
        # create some players
        self.cache.insert('arthur', 'red', False)
        self.cache.insert('bob', 'blue', True) # GM
        self.cache.insert('carlos', 'yellow', False)
        
        # query players
        cache1 = self.cache.get('arthur')
        self.assertIsNotNone(cache1)
        cache2 = self.cache.get('bob')
        self.assertIsNotNone(cache2)
        cache3 = self.cache.get('carlos')
        self.assertIsNotNone(cache3)
        
        # removed player cannot be queried
        self.cache.remove('bob')
        cache2 = self.cache.get('bob')
        self.assertIsNone(cache2)
        
        # cannot query unknown player 
        unknown_cache = self.cache.get('gabriel')
        self.assertIsNone(unknown_cache)
        
    def test_getData(self): 
        # create some players
        self.cache.insert('arthur', 'red', False)
        self.cache.insert('gabriel', 'red', False)
        self.cache.insert('carlos', 'yellow', False)
        self.cache.insert('bob', 'blue', True)
        
        # query data (in index-order)
        data = self.cache.getData()
        self.assertEqual(len(data), 4)
        self.assertEqual(data[0]['name'], 'arthur')
        self.assertEqual(data[1]['name'], 'gabriel')
        self.assertEqual(data[2]['name'], 'carlos')
        self.assertEqual(data[3]['name'], 'bob')
        
        # remove player
        self.cache.remove('carlos')
        # re- query data (in index-order)
        data = self.cache.getData()
        self.assertEqual(len(data), 3)
        self.assertEqual(data[0]['name'], 'arthur')
        self.assertEqual(data[1]['name'], 'gabriel')
        self.assertEqual(data[2]['name'], 'bob')
        
    def test_getSelections(self):  
        # create some players
        self.cache.insert('arthur', 'red', False)
        self.cache.insert('gabriel', 'red', False)
        self.cache.insert('carlos', 'yellow', False)
        self.cache.insert('bob', 'blue', True)
        
        # set selections
        self.cache.get('arthur').selected = [236, 154]
        self.cache.get('carlos').selected = [12]
        self.cache.get('bob').selected = [124, 236, 12]
        
        # expect selections per player name
        selections = self.cache.getSelections()
        for name in selections:
            self.assertEqual(selections[name], self.cache.get(name).selected)
        
    def test_remove(self):  
        # create some players
        self.cache.insert('arthur', 'red', False)
        self.cache.insert('gabriel', 'red', False)
        self.cache.insert('carlos', 'yellow', False)
        self.cache.insert('bob', 'blue', True)
        
        # remove but expect indices being rebuilt
        self.cache.remove('carlos')
        ids = set()
        for name in self.cache.players:
            ids.add(self.cache.players[name].index)
        self.assertEqual(len(ids), 3)
        self.assertEqual(ids, {0, 1, 2})
        
        # cannot remove player twice
        with self.assertRaises(KeyError):
            self.cache.remove('carlos')
        
        # cannot remove unknown player
        with self.assertRaises(KeyError):
            self.cache.remove('dimitri')
        
    # @NOTE: other operations are tested during integration test
