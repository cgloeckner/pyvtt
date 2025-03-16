"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2022 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import datetime
import os
import random
import time

from bottle import response
from pony.orm import db_session

from test.common import EngineBaseTest


class GmTest(EngineBaseTest):
    
    @db_session
    def test_postSetup(self):
        # create demo GM
        gm = self.engine.main_db.GM(name='user123', url='url456', identity='user123', sid='123456')
        gm.post_setup()
        
        # test call of makeLock()
        self.assertIn(gm.url, self.engine.storage.locks)
        
        # test GM's Path
        p = self.engine.paths.get_gms_path(gm.url)
        self.assertTrue(os.path.exists(p))
        
        # test GM being in engine's cache
        gm_cache = self.engine.cache.get(gm)
        self.assertIsNotNone(gm_cache)

    def test_hasExpired(self):
        with db_session:
            gm = self.engine.main_db.GM(name='user123', url='url456', identity='user123', sid='123456')
            gm.post_setup()
            now = int(time.time())

        gm_cache = self.engine.cache.insert(gm)
        gm_cache.connect_db()

        with db_session:
            gm = self.engine.main_db.GM.select(url=gm.url).first()

            # has not expired yet
            gm.timeid = int(now - self.engine.cleanup['expire'] * 0.75)
            self.assertFalse(gm.has_expired(now, gm_cache.db))

            # has expired
            gm.timeid = int(now - self.engine.cleanup['expire'] * 1.2)
            self.assertTrue(gm.has_expired(now, gm_cache.db))

    def test_gm_is_not_expired_if_has_recent_games(self) -> None:
        now = int(time.time())

        with db_session:
            gm = self.engine.main_db.GM(name='user123', url='url456', identity='user123', sid='123456')
            gm.post_setup()

        gm_cache = self.engine.cache.insert(gm)
        gm_cache.connect_db()

        with db_session:
            gm = self.engine.main_db.GM.select(url=gm.url).first()
            gm.timeid = 1
            self.assertTrue(gm.has_expired(now, gm_cache.db))

        with db_session:
            game = gm_cache.db.Game(url='test-game', gm_url=gm.url)
            game.post_setup()

            game.timeid = 1
            self.assertTrue(game.has_expired(now, 1.0))
            self.assertTrue(gm.has_expired(now, gm_cache.db))

            game.timeid = now
            self.assertFalse(game.has_expired(now, 1.0))
            self.assertFalse(gm.has_expired(now, gm_cache.db))

    def test_cleanup(self):
        with db_session:
            # create demo GM
            gm = self.engine.main_db.GM(name='user123', url='url456', identity='user123', sid='123456')
            gm.post_setup()
        
        gm_cache = self.engine.cache.get(gm)
        gm_cache.connect_db()
        
        with db_session:
            # create some games
            g1 = gm_cache.db.Game(url='foo', gm_url='url456')
            g1.post_setup()
            g2 = gm_cache.db.Game(url='bar', gm_url='url456')
            g2.timeid = time.time() - self.engine.cleanup['expire'] - 10
            g2.post_setup()
            
            # create some rolls
            now = time.time()
            old = now - self.engine.latest_rolls - 10
            for i in range(15):
                gm_cache.db.Roll(game=g1, name='test', color='red', sides=20, result=random.randrange(1, 20),
                                 timeid=now)
                gm_cache.db.Roll(game=g2, name='test', color='red', sides=20, result=random.randrange(1, 20),
                                 timeid=now)
            for i in range(45):
                gm_cache.db.Roll(game=g1, name='test', color='red', sides=12, result=random.randrange(1, 12),
                                 timeid=old)
                gm_cache.db.Roll(game=g2, name='test', color='red', sides=12, result=random.randrange(1, 12),
                                 timeid=old)
            all_rolls = gm_cache.db.Roll.select()
            self.assertEqual(len(all_rolls), 120)
            
            # trigger cleanup
            g, i, r, t, m = gm.cleanup(gm_cache.db, now)
            self.assertEqual(g, ['url456/bar'])
            self.assertEqual(i, 4096)
            self.assertEqual(r, 45)
            self.assertEqual(t, 0)
            self.assertEqual(m, 0)
            
            # expect first game to still exist
            q1 = gm_cache.db.Game.select(lambda _g: _g.url == 'foo').first()
            self.assertEqual(g1, q1)
            # with only 15 rolls left
            g1_rolls = gm_cache.db.Roll.select(lambda _r: _r.game == q1)
            self.assertEqual(len(g1_rolls), 15)
            for r in g1_rolls:  # expect no d12 rolls (they were deleted)
                self.assertEqual(r.sides, 20)
            
            # expect second game to be deleted
            q2 = gm_cache.db.Game.select(lambda _g: _g.url == 'bar').first()
            self.assertIsNone(q2)
            # so only 15 rolls remain in total 
            all_rolls = gm_cache.db.Roll.select()
            self.assertEqual(len(all_rolls), 15)
        
    def test_preDelete(self):
        with db_session:
            # create demo GM
            gm = self.engine.main_db.GM(name='user123', url='url456', identity='user123', sid='123456')
            gm.post_setup()
        
        gm_cache = self.engine.cache.get(gm)
        gm_cache.connect_db()
        
        with db_session:
            # create some games
            g1 = gm_cache.db.Game(url='foo', gm_url='url456')
            g1.post_setup()
            g2 = gm_cache.db.Game(url='bar', gm_url='url456')
            g2.post_setup()
            
            # create some rolls
            now = time.time()
            for i in range(15):
                gm_cache.db.Roll(game=g1, name='test', color='red', sides=20,
                                 result=random.randrange(1, 20), timeid=now)
                gm_cache.db.Roll(game=g2, name='test', color='red', sides=20,
                                 result=random.randrange(1, 20), timeid=now)
            all_rolls = gm_cache.db.Roll.select()
            self.assertEqual(len(all_rolls), 30)
        
        # prepare pre-deletion
        gm.pre_delete()
        
        # expect directory and cache instance being removed  
        p = self.engine.paths.get_gms_path(gm.url)
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
        gm = self.engine.main_db.GM(name='user123', url='url456', identity='user123', sid='123456')
        gm.post_setup()
        
        # setup session
        day_ago = time.time() - 3600 * 24
        gm.sid = self.engine.main_db.GM.generate_session()
        gm.timeid = day_ago
        
        # refresh session
        gm.refresh_session(response)
        self.assertGreater(gm.timeid, day_ago)
        
        # check cookie being set
        cookies = [value for name, value in response.headerlist if name.title() == 'Set-Cookie']
        cookies.sort()
        expire_date = gm.timeid + self.engine.cleanup['expire']
        time_str = (datetime.datetime.fromtimestamp(expire_date).astimezone(datetime.timezone.utc).
                    strftime('%a, %d %b %Y %H:%M:%S GMT'))
        self.assertIn('session={0}'.format(gm.sid), cookies[0])
        self.assertIn('expires={0}'.format(time_str), cookies[0])
        
    def test_loadFromSession(self):
        with db_session:
            # create demo GM
            gm = self.engine.main_db.GM(name='user123', url='url456', identity='user123', sid='123456')
            gm.post_setup()
            gm.sid = self.engine.main_db.GM.generate_session()
        
        # create fake-request
        class FakeRequest(object):
            def __init__(self, session):
                self.session = session

            def get_cookie(self, _):
                return self.session
        
        request = FakeRequest(gm.sid)
        
        # load GM from session
        with db_session:
            loaded = self.engine.main_db.GM.load_from_session(request)
            self.assertEqual(loaded.id, gm.id)
        
