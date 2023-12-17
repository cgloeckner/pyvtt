#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2022 Christian Glöckner
License: MIT (see LICENSE for details)
"""

from pony.orm import db_session

from test.common import EngineBaseTest, SocketDummy


class EngineCacheTest(EngineBaseTest):
        
    def test_insert(self):     
        cache = self.engine.cache
        
        # @NOTE: first insertion is trigged by postSetup()
        with db_session:
            gm1 = self.engine.main_db.GM(name='foo', url='foo', identity='foo', sid='123')
            gm2 = self.engine.main_db.GM(name='bar', url='bar', identity='bar', sid='456')
            gm1.post_setup()
            gm2.post_setup()
        
        # 2nd insertion is fine (GmCache is replaced)
        # @NOTE: the user may delete cookies and relogin
        cache.insert(gm1)
        
    def test_get(self):  
        cache = self.engine.cache
        
        with db_session:
            gm1 = self.engine.main_db.GM(name='foo', url='foo', identity='foo', sid='123')
            gm2 = self.engine.main_db.GM(name='bar', url='bar', identity='bar', sid='456')
            gm1.post_setup()
            gm2.post_setup()
        
        # different GMs have different cache instances
        gm1_cache = cache.get(gm1)
        gm2_cache = cache.get(gm2)
        self.assertNotEqual(gm1_cache, gm2_cache)
        
    def getFromUrl(self):   
        cache = self.engine.cache
        
        with db_session:
            gm1 = self.engine.main_db.GM(name='foo', url='foo', identity='foo', sid='123')
            gm2 = self.engine.main_db.GM(name='bar', url='bar', identity='bar', sid='456')
            gm1.post_setup()
            gm2.post_setup()
        
        # different GMs have different cache instances
        gm1_cache = cache.get_from_url(gm1.url)
        gm2_cache = cache.get_from_url(gm2.url)
        self.assertNotEqual(gm1_cache, gm2_cache)
        
        # not failing but returns None for unknown GM
        unknown_cache = cache.get_from_url('some-random-bullshit')
        self.assertIsNone(unknown_cache)
        
    def test_remove(self):  
        cache = self.engine.cache
        
        with db_session:
            gm1 = self.engine.main_db.GM(name='foo', url='foo', identity='foo', sid='123')
            gm2 = self.engine.main_db.GM(name='bar', url='bar', identity='bar', sid='456')
            gm1.post_setup()
            gm2.post_setup()
        
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
        cache = self.engine.cache

        # create GM
        with db_session:
            gm = self.engine.main_db.GM(name='foo', url='foo', identity='foo', sid='123')
            gm.post_setup()
        gm_cache = cache.get(gm)
        gm_cache.connect_db()

        # create Game
        with db_session:
            game = gm_cache.db.Game(url='bar', gm_url='foo')
            game.post_setup()
        game_cache = gm_cache.get(game)
        self.assertEqual(len(game_cache.players), 0)

        # cannot listen to empty socket
        socket = SocketDummy()
        socket.block = False   
        ret = cache.listen(socket)
        self.assertIsNone(ret)

        # cannot listen if not logged in
        socket = SocketDummy()
        socket.block = False   
        socket.push_receive({'name': 'arthur', 'gm_url': 'foo', 'game_url': 'bar'})
        cache.listen(socket)   
        ret = cache.listen(socket)
        self.assertIsNone(ret)

        # create Player
        player_cache = game_cache.insert('arthur', 'red', is_gm=False)

        # listening to a silent socket does not trigger handle
        socket = SocketDummy()
        socket.block = False
        cache.listen(socket)
        self.assertIsNone(player_cache.socket)
        self.assertIsNone(player_cache.greenlet)

        # listening for invalid GM's game does not trigger handle
        socket.push_receive({'name': 'arthur', 'gm_url': 'weird', 'game_url': 'bar'})
        cache.listen(socket)
        self.assertIsNone(player_cache.socket)
        self.assertIsNone(player_cache.greenlet)
        
        # listening for invalid game does not trigger handle
        socket.push_receive({'name': 'arthur', 'gm_url': 'foo', 'game_url': 'weird'})
        cache.listen(socket)
        self.assertIsNone(player_cache.socket)
        self.assertIsNone(player_cache.greenlet)

        # listening adds a player triggers handle
        socket.block = False
        socket.push_receive({'name': 'arthur', 'gm_url': 'foo', 'game_url': 'bar'})
        cache.listen(socket)
        self.assertEqual(player_cache.socket, socket)
        self.assertIsNotNone(player_cache.greenlet)
        
        # @NOTE: The async handle() will terminate, because the dummy
        # socket yields None and hence mimics socket to be closed by
        # the client .. wait for it!  
        player_cache.greenlet.join()
        
        # expect player to be disconnected
        player_cache = game_cache.get('arthur')
        self.assertIsNone(player_cache)
