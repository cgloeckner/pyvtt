#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import os, time, random, datetime

from bottle import response
from pony.orm import db_session

import orm

from test.utils import EngineBaseTest

class GmTest(EngineBaseTest):
    
    @db_session
    def test_postSetup(self):
        # create demo GM
        gm = self.engine.main_db.GM(name='user123', url='url456', sid='123456')
        gm.postSetup()
        
        # test call of makeLock()
        self.assertIn(gm.url, self.engine.locks)
        
        # test GM's Path
        p = self.engine.paths.getGmsPath(gm.url)
        self.assertTrue(os.path.exists(p))
        
        # test GM being in engine's cache
        gm_cache = self.engine.cache.get(gm)
        self.assertIsNotNone(gm_cache)
        
    def test_cleanup(self):
        with db_session:
            # create demo GM
            gm = self.engine.main_db.GM(name='user123', url='url456', sid='123456')
            gm.postSetup()
        
        gm_cache = self.engine.cache.get(gm)
        gm_cache.connect_db()
        
        with db_session:
            # create some games
            g1 = gm_cache.db.Game(url='foo', gm_url='url456')
            g1.postSetup()
            g2 = gm_cache.db.Game(url='bar', gm_url='url456')
            g2.timeid = time.time() - self.engine.expire - 10
            g2.postSetup()
            
            # create some rolls
            now = time.time()
            old = now - self.engine.latest_rolls - 10
            for i in range(15):
                gm_cache.db.Roll(game=g1, name='test', color='red',
                    sides=20, result=random.randrange(1, 20), timeid=now)
                gm_cache.db.Roll(game=g2, name='test', color='red',
                    sides=20, result=random.randrange(1, 20), timeid=now)
            for i in range(45):
                gm_cache.db.Roll(game=g1, name='test', color='red',
                    sides=12, result=random.randrange(1, 12), timeid=old)
                gm_cache.db.Roll(game=g2, name='test', color='red',
                    sides=12, result=random.randrange(1, 12), timeid=old)
            all_rolls = gm_cache.db.Roll.select()
            self.assertEqual(len(all_rolls), 120)
            
            # trigger cleanup
            gm.cleanup(gm_cache.db, now)
            
            # expect first game to still exist
            q1 = gm_cache.db.Game.select(lambda g: g.url == 'foo').first()
            self.assertEqual(g1, q1)
            # with only 15 rolls left
            g1_rolls = gm_cache.db.Roll.select(lambda r: r.game == q1)
            self.assertEqual(len(g1_rolls), 15)
            for r in g1_rolls: # expect no d12 rolls (they were deleted)
                self.assertEqual(r.sides, 20)
            
            # expect second game to be deleted
            q2 = gm_cache.db.Game.select(lambda g: g.url == 'bar').first()
            self.assertIsNone(q2)
            # so only 15 rolls remain in total 
            all_rolls = gm_cache.db.Roll.select()
            self.assertEqual(len(all_rolls), 15)
        
    def test_preDelete(self):
        with db_session:
            # create demo GM
            gm = self.engine.main_db.GM(name='user123', url='url456', sid='123456')
            gm.postSetup()
        
        gm_cache = self.engine.cache.get(gm)
        gm_cache.connect_db()
        
        with db_session:
            # create some games
            g1 = gm_cache.db.Game(url='foo', gm_url='url456')
            g1.postSetup()
            g2 = gm_cache.db.Game(url='bar', gm_url='url456')
            g2.postSetup()
            
            # create some rolls
            now = time.time()
            old = now - self.engine.latest_rolls - 10
            for i in range(15):
                gm_cache.db.Roll(game=g1, name='test', color='red',
                    sides=20, result=random.randrange(1, 20), timeid=now)
                gm_cache.db.Roll(game=g2, name='test', color='red',
                    sides=20, result=random.randrange(1, 20), timeid=now)
            all_rolls = gm_cache.db.Roll.select()
            self.assertEqual(len(all_rolls), 30)
        
        # prepare pre-deletion
        gm.preDelete()
        
        # expect directory and cache instance being removed  
        p = self.engine.paths.getGmsPath(gm.url)
        self.assertFalse(os.path.exists(p))
        gm_cache = self.engine.cache.get(gm)
        self.assertIsNone(gm_cache)
        
        # delete GM
        with db_session:
            gm = self.engine.main_db.GM.select(lambda g: g.url == 'url456').first()
            gm.delete()
        
    @db_session
    def test_refreshSession(self):
        # create demo GM
        gm = self.engine.main_db.GM(name='user123', url='url456', sid='123456')
        gm.postSetup()
        
        # setup session
        day_ago   = time.time() - 3600 * 24
        gm.sid    = self.engine.main_db.GM.genSession()
        gm.timeid = day_ago
        
        # refresh session
        gm.refreshSession(response)
        self.assertGreater(gm.timeid, day_ago)
        
        # check cookie being set
        cookies = [value for name, value in response.headerlist
            if name.title() == 'Set-Cookie']
        cookies.sort()
        expire_date = gm.timeid + self.engine.expire
        time_str = datetime.datetime.fromtimestamp(expire_date).astimezone(datetime.timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')
        self.assertIn('session={0}'.format(gm.sid), cookies[0])
        self.assertIn('expires={0}'.format(time_str), cookies[0])
        
    def test_loadFromSession(self):
        with db_session:
            # create demo GM
            gm = self.engine.main_db.GM(name='user123', url='url456', sid='123456')
            gm.postSetup()
            gm.sid = self.engine.main_db.GM.genSession()
        
        # create fake-request
        class FakeRequest(object):
            def __init__(self, session):
                self.session = session
            def get_cookie(self, key):
                return self.session
        
        request = FakeRequest(gm.sid)
        
        # load GM from session
        with db_session:
            loaded = self.engine.main_db.GM.loadFromSession(request)
            self.assertEqual(loaded.id, gm.id)
        
