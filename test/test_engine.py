"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2022 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import json
import os
import random
import requests
import tempfile
import time

import gevent
from bottle import FileUpload
from pony.orm import db_session

from test.common import EngineBaseTest
from vtt import engine


class EngineTest(EngineBaseTest):
        
    def tearDown(self):
        super().tearDown()
        
    @staticmethod
    def defaultEnviron():
        os.environ['VTT_TITLE'] = 'unittest'
        os.environ['VTT_LIMIT_TOKEN'] =' 2'
        os.environ['VTT_LIMIT_BG'] = '10'
        os.environ['VTT_LIMIT_GAME'] = '5'
        os.environ['VTT_LIMIT_MUSIC'] = '10'
        os.environ['VTT_NUM_MUSIC'] = '5'
        os.environ['VTT_CLEANUP_EXPIRE'] = '3600'
        os.environ['VTT_CLEANUP_TIME'] = '03:00'
        os.environ['VTT_DOMAIN'] = 'vtt.example.com'
        os.environ['VTT_PORT'] = '8080'
        os.environ.pop('VTT_SSL', None)
        os.environ.pop('VTT_REVERSE_PROXY', None)

    def reloadEngine(self, argv=list()):
        # reload engine (without cleanup thread)
        argv.append('--quiet')
        self.engine = engine.Engine(argv=argv, pref_dir=self.root)

        self.monkeyPatch()

    def test_run_engine_with_custom_prefdir(self):
        engine.Engine(argv=['--prefdir=/tmp'])
        

    def test_run(self): 
        # confirm server is offline
        with self.assertRaises(requests.exceptions.ConnectionError):
            requests.get('http://localhost:8080')
        
        # start and query server
        greenlet = gevent.Greenlet(run=self.engine.run)
        greenlet.start()
        ret = requests.get('http://localhost:8080')
        self.assertIsNotNone(ret)
        
        # confirm server is offline again
        gevent.kill(greenlet)
        with self.assertRaises(requests.exceptions.ConnectionError):
            requests.get('http://localhost:8080')
        
    def test_getDomain(self):
        EngineTest.defaultEnviron()
        os.environ['VTT_DOMAIN'] = 'example.com'
        self.reloadEngine()
        
        domain = self.engine.get_domain()
        self.assertEqual(domain, 'example.com')
        
        # reload with --localhost
        self.reloadEngine(argv=['--localhost'])
        domain = self.engine.get_domain()
        self.assertEqual(domain, 'localhost')
        
    def test_getPort(self):
        EngineTest.defaultEnviron()
        p = self.engine.get_port()
        self.assertEqual(p, 8080)
        
        # reload with custom port
        os.environ['VTT_PORT'] = '80'
        self.reloadEngine()
        p = self.engine.get_port()
        self.assertEqual(p, 80)
        
    def test_hasSsl(self):
        EngineTest.defaultEnviron()
        self.reloadEngine()
        self.assertFalse(self.engine.has_ssl())
        
        # reload with ssl
        os.environ['VTT_SSL'] = 'True'
        self.reloadEngine()   
        self.assertTrue(self.engine.has_ssl())

    def test_getUrl(self):
        EngineTest.defaultEnviron()
        self.reloadEngine()
        self.assertEqual(self.engine.get_url(), 'http://vtt.example.com:8080')

        # internal SSL does not effect it
        os.environ['VTT_SSL'] = 'True'
        self.reloadEngine()
        self.assertEqual(self.engine.get_url(), 'https://vtt.example.com:8080')

        # internal port does not effect it
        os.environ['VTT_PORT'] = '443'
        self.reloadEngine()
        self.assertEqual(self.engine.get_url(), 'https://vtt.example.com')
        
    def test_getWebsocketUrl(self):
        EngineTest.defaultEnviron()
        self.reloadEngine()
        self.assertEqual(self.engine.get_websocket_url(), 'ws://vtt.example.com:8080/vtt/websocket')

        # internal SSL does not effect it
        os.environ['VTT_SSL'] = 'True'
        self.reloadEngine()
        self.assertEqual(self.engine.get_websocket_url(), 'wss://vtt.example.com:8080/vtt/websocket')

        # internal port does not effect it
        os.environ['VTT_SSL'] = 'True'
        os.environ['VTT_PORT'] = '443'
        self.reloadEngine()
        self.assertEqual(self.engine.get_websocket_url(), 'wss://vtt.example.com/vtt/websocket')
        
    def test_getBuildSha(self):
        self.engine.git_hash = None
        self.engine.debug_hash = None
        v = self.engine.get_build_sha()
        self.assertEqual(v, self.engine.version)

        self.engine.git_hash = 'deadbeef'
        v = self.engine.get_build_sha()
        self.assertEqual(v, f'{self.engine.version}-{self.engine.git_hash}')

        self.engine.debug_hash = 'abcdefghijklmnop'
        v = self.engine.get_build_sha()
        self.assertEqual(v, self.engine.debug_hash)
        
        self.engine.git_hash = None
        v = self.engine.get_build_sha()
        self.assertEqual(v, self.engine.debug_hash)

    def test_getAuthCallbackUrl(self):
        EngineTest.defaultEnviron()
        self.reloadEngine()
        self.assertEqual(self.engine.get_auth_callback_url(), 'http://vtt.example.com:8080/vtt/callback')

        # internal SSL does not effect it
        os.environ['VTT_SSL'] = 'True'
        self.reloadEngine()
        self.assertEqual(self.engine.get_auth_callback_url(), 'https://vtt.example.com:8080/vtt/callback')

        # internal port does not effect it
        os.environ['VTT_PORT'] = '443'
        self.reloadEngine()
        self.assertEqual(self.engine.get_auth_callback_url(), 'https://vtt.example.com/vtt/callback')
        
    def test_verifyUrlSection(self):
        self.assertTrue(self.engine.verify_url_section('foo-bar.lol_test'))
        self.assertFalse(self.engine.verify_url_section('url-with-speciöl-char'))
        self.assertFalse(self.engine.verify_url_section('test-with-{braces'))
        self.assertFalse(self.engine.verify_url_section('url with-space'))
        # idk...
        
    def test_getClientIp(self):
        class FakeRequest(object):
            def __init__(self, proxy = False):
                class FakeEnviron(object):
                    def __init__(self, proxy = False):
                        self.proxy = proxy
                    def get(self, s):
                        if not self.proxy and s == 'REMOTE_ADDR':
                            return '1.2.3.4'
                        if not self.proxy and s == 'HTTP_X_FORWARDED_FOR':
                            return None
                        else:
                            return '5.6.7.8'
                self.environ = FakeEnviron(proxy)
        
        dummy_request = FakeRequest()
        self.assertEqual(self.engine.get_client_ip(dummy_request), '1.2.3.4')
        dummy_request = FakeRequest(True)
        self.assertEqual(self.engine.get_client_ip(dummy_request), '5.6.7.8')
        
    def test_getClientAgent(self):
        class FakeRequest(object):
            def __init__(self):
                class FakeEnviron(object):
                    def get(self, s):
                        if s == 'HTTP_USER_AGENT':
                            return 'Fake Browser'
                        return None
                self.environ = FakeEnviron()
        
        dummy_request = FakeRequest()
        self.assertEqual(self.engine.get_client_agent(dummy_request), 'Fake Browser')
        
    def test_getCountryFromIp(self):
        # only test that the external API is working
        # @NOTE: method got monkeypatched
        code = self.prev_getCountryFromIp('127.0.0.1')
        self.assertIsInstance(code, str)
        
    def test_getPublicIp(self):
        # only test that the external API is working 
        # @NOTE: method got monkeypatched
        ip = self.prev_getPublicIp()
        self.assertIsInstance(ip, str)
        
    def test_getMd5(self):
        # NOTE: THIS file here is hashed
        with open(__file__, 'rb') as h:
            ret = self.engine.get_md5(h)
            self.assertIsInstance(ret, str)
        
    def test_getSize(self):
        # create dummy file
        with tempfile.TemporaryFile() as h:
            h.write(b'0' * 4953)
            
            # rewind for reading
            h.seek(0)
            fupload = FileUpload(h, 'demo.dat', 'demo.dat')
            size = self.engine.get_size(fupload)
            self.assertEqual(size, 4953)
        
    def test_getSupportedDice(self):
        dice = self.engine.get_supported_dice()
        self.assertEqual(dice, [2, 4, 6, 8, 10, 12, 20, 100])
        
    def test_cleanup(self):
        now = time.time()
        
        with db_session:
            # create GMs
            gm1 = self.engine.main_db.GM(name='user123', url='url456', identity='user123', sid='123456')
            gm1.post_setup()
            gm2 = self.engine.main_db.GM(name='nobody', url='second', identity='nobody', sid='5673')
            gm2.post_setup()
            gm2.timeid = now - self.engine.cleanup['expire'] - 10
        
        gm1_cache = self.engine.cache.get(gm1)
        gm1_cache.connect_db()
        gm2_cache = self.engine.cache.get(gm2)
        gm2_cache.connect_db()
        
        with db_session:
            # create some games
            g1 = gm1_cache.db.Game(url='foo', gm_url='url456')
            g1.post_setup()
            g2 = gm1_cache.db.Game(url='bar', gm_url='url456')
            g2.timeid = time.time() - self.engine.cleanup['expire'] - 10
            g2.post_setup()
            
            # create some rolls
            old = now - self.engine.latest_rolls - 10
            for i in range(15):
                gm1_cache.db.Roll(game=g1, name='test', color='red',
                    sides=20, result=random.randrange(1, 20), timeid=now)
                gm1_cache.db.Roll(game=g2, name='test', color='red',
                    sides=20, result=random.randrange(1, 20), timeid=now)
            for i in range(45):
                gm1_cache.db.Roll(game=g1, name='test', color='red',
                    sides=12, result=random.randrange(1, 12), timeid=old)
                gm1_cache.db.Roll(game=g2, name='test', color='red',
                    sides=12, result=random.randrange(1, 12), timeid=old)
            all_rolls = gm1_cache.db.Roll.select()
            self.assertEqual(len(all_rolls), 120)
            
            # export both games
            g1.to_zip()
            g2.to_zip()
            export_path = self.engine.paths.get_export_path()
            num_files = len(os.listdir(export_path))
            self.assertEqual(num_files, 2)
            
            # cleanup!
            gms, games, zips, b, r, t, m = self.engine.cleanup_all()
            self.assertEqual(gms, ['second']) 
            self.assertEqual(games, ['url456/bar'])
            self.assertEqual(zips, 2)
            self.assertEqual(b, 12288)
            self.assertEqual(r, 0)
            self.assertEqual(t, 0)
            self.assertEqual(m, 0)
            
            # expect first game to still exist
            q1 = gm1_cache.db.Game.select(lambda g: g.url == 'foo').first()
            self.assertEqual(g1, q1)
            # with only 15 rolls left
            g1_rolls = gm1_cache.db.Roll.select(lambda r: r.game == q1)
            self.assertEqual(len(g1_rolls), 15)
            for r in g1_rolls: # expect no d12 rolls (they were deleted)
                self.assertEqual(r.sides, 20)
            
            # expect second game to be deleted
            q2 = gm1_cache.db.Game.select(lambda g: g.url == 'bar').first()
            self.assertIsNone(q2)
            # so only 15 rolls remain in total 
            all_rolls = gm1_cache.db.Roll.select()
            self.assertEqual(len(all_rolls), 15)
            
            # expect second GM to be deleted
            gm2_ = self.engine.main_db.GM.select(lambda g: g.url == 'second').first()
            self.assertIsNone(gm2_)
            
            # expect all ZIPs being removed
            num_files = len(os.listdir(export_path))
            self.assertEqual(num_files, 0)

    def test_saveToDict(self):
        with db_session:
            # create GMs
            gm1 = self.engine.main_db.GM(name='user123', url='url456', identity='user123', sid='123456')
            gm1.post_setup()
            gm2 = self.engine.main_db.GM(name='nobody', url='second', identity='nobody', sid='5673')
            gm2.post_setup()
        
        gm1_cache = self.engine.cache.get(gm1)
        gm1_cache.connect_db()
        gm2_cache = self.engine.cache.get(gm2)
        gm2_cache.connect_db()
        
        with db_session:
            # create some games
            g1 = gm1_cache.db.Game(url='foo', gm_url='second')
            g1.post_setup()
            g2 = gm1_cache.db.Game(url='bar', gm_url='second')
            g2.timeid = time.time() - self.engine.cleanup['expire'] - 10
            g2.post_setup()
            g3 = gm2_cache.db.Game(url='bar', gm_url='url456')
            g3.timeid = time.time() - self.engine.cleanup['expire'] - 10
            g3.post_setup()

        export = self.engine.save_to_dict()

        # check GM data
        self.assertEqual(len(export), 2)
        self.assertEqual(export[0]['name'], gm1.name)
        self.assertEqual(export[0]['url'],  gm1.url)
        self.assertEqual(export[0]['sid'],  gm1.sid)
        self.assertEqual(export[1]['name'], gm2.name)
        self.assertEqual(export[1]['url'],  gm2.url)
        self.assertEqual(export[1]['sid'],  gm2.sid)

        # check Games Data
        self.assertEqual(len(export[0]['games']), 2)
        self.assertIn('bar', export[0]['games'])  
        self.assertIn('foo', export[0]['games']) 
        
        self.assertEqual(len(export[1]['games']), 1)   
        self.assertIn('bar', export[1]['games'])
         
    def test_loadFromDict(self):
        data = [{
            'name': 'otto',
            'url' : '12345',
            'sid' : 'foobar1234',
            'identity' : 'foo@bar.com',
            'metadata' : 'additional info',
            'games': {
                'test': {
                    'tokens': [{'url': 5, 'posx': 12, 'posy': 34, 'zorder': 56, 'size': 120, 'rotate': 22.5, 'flipx': True, 'locked': True}],
                    'scenes': [{'tokens': [0], 'backing': None}]
                }
            }
        }]

        self.engine.load_from_dict(data)

        # check GM data
        with db_session:
            all_gms = list(self.engine.main_db.GM.select())
        self.assertEqual(len(all_gms), 1)
        self.assertEqual(all_gms[0].name, 'otto')
        self.assertEqual(all_gms[0].url, '12345')
        self.assertEqual(all_gms[0].sid, 'foobar1234')
        self.assertEqual(all_gms[0].identity, 'foo@bar.com')
        self.assertEqual(all_gms[0].metadata, 'additional info')

        # check Games Data
        gm_cache = self.engine.cache.get_from_url('12345')
        with db_session:
            all_games = list(gm_cache.db.Game.select())
        self.assertEqual(len(all_games), 1)

