#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import os, json, tempfile, time, random, requests

from bottle import FileUpload 
from pony.orm import db_session
import gevent

import engine

from test.utils import EngineBaseTest

class EngineTest(EngineBaseTest):
        
    def tearDown(self):
        fname = self.engine.paths.getSettingsPath()
        if os.path.exists(fname):
            os.remove(fname)
        
        super().tearDown()
        
    @staticmethod
    def defaultSettings():
        return {
            'title'      : 'unittest',
            'links'      : list(),
            'file_limit' : {
                'token'      : 2,
                'background' : 10,
                'game'       : 15,
                'music'      : 10,
                'num_music'  : 5
            },
            'playercolors' : ['#FF0000', '#00FF00'],
            'shards'     : list(),
            'expire'     : 3600,
            'hosting'    : {
                'domain' : 'vtt.example.com',
                'port'   : 80,
                'ssl'    : False
            },
            'login'      : {
                'type'   : None
            },
            'notify'     : {
                'type'   : None
            }
        }
        
    def reloadEngine(self, argv=list(), settings=None):
        if settings is not None:
            # change settings
            fname = self.engine.paths.getSettingsPath()
            with open(fname, 'w') as h:
                json.dump(settings, h)
        
        # reload engine
        argv.append('--quiet')
        self.engine = engine.Engine(argv=argv, pref_dir=self.root)
        
        self.monkeyPatch()
        
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
        settings = EngineTest.defaultSettings()
        settings['hosting']['domain'] = 'example.com'
        self.reloadEngine(settings=settings)
        
        domain = self.engine.getDomain()
        self.assertEqual(domain, 'example.com')
        
        # reload with --localhost
        self.reloadEngine(argv=['--localhost'], settings=settings)
        domain = self.engine.getDomain()
        self.assertEqual(domain, 'localhost')
        
    def test_getPort(self):
        p = self.engine.getPort()
        self.assertEqual(p, 8080)
        
        # reload with custom port
        settings = EngineTest.defaultSettings()
        settings['hosting']['port'] = 80
        self.reloadEngine(settings=settings)
        p = self.engine.getPort()
        self.assertEqual(p, 80)
        
    def test_hasSsl(self):
        self.assertFalse(self.engine.hasSsl())
        
        # reload with ssl
        settings = EngineTest.defaultSettings()
        settings['hosting']['ssl'] = True 
        self.reloadEngine(settings=settings)   
        self.assertTrue(self.engine.hasSsl())
        
    def test_getUrl(self):
        settings = EngineTest.defaultSettings()
        self.reloadEngine(settings=settings)
        self.assertEqual(self.engine.getUrl(), 'http://vtt.example.com:80')

        # reload with ssl
        settings['hosting']['ssl'] = True
        self.reloadEngine(settings=settings)
        self.assertEqual(self.engine.getUrl(), 'https://vtt.example.com:80')

        # reload with a different port
        settings['hosting']['port'] = 443
        self.reloadEngine(settings=settings)
        self.assertEqual(self.engine.getUrl(), 'https://vtt.example.com:443')
        
    def test_getWebsocketUrl(self):
        settings = EngineTest.defaultSettings()
        self.reloadEngine(settings=settings)
        self.assertEqual(self.engine.getWebsocketUrl(), 'wss://vtt.example.com:80/websocket')

        # internal SSL does not effect it
        settings['hosting']['ssl'] = False
        self.reloadEngine(settings=settings)
        self.assertEqual(self.engine.getWebsocketUrl(), 'wss://vtt.example.com/websocket')

        # internal port does not effect it
        settings['hosting']['port'] = 443
        self.reloadEngine(settings=settings)
        self.assertEqual(self.engine.getWebsocketUrl(), 'wss://vtt.example.com/websocket')
        
    def test_getAuthCallbackUrl(self):
        settings = EngineTest.defaultSettings()
        self.reloadEngine(settings=settings)
        self.assertEqual(self.engine.getAuthCallbackUrl(), 'https://vtt.example.com/vtt/callback')

        # internal SSL does not effect it
        settings['hosting']['ssl'] = False
        self.reloadEngine(settings=settings)
        self.assertEqual(self.engine.getAuthCallbackUrl(), 'https://vtt.example.com/vtt/callback')

        # internal port does not effect it
        settings['hosting']['port'] = 443
        self.reloadEngine(settings=settings)
        self.assertEqual(self.engine.getAuthCallbackUrl(), 'https://vtt.example.com/vtt/callback')
        
    def test_verifyUrlSection(self):
        self.assertTrue(self.engine.verifyUrlSection('foo-bar.lol_test'))
        self.assertFalse(self.engine.verifyUrlSection('url-with-speciöl-char'))
        self.assertFalse(self.engine.verifyUrlSection('test-with-{braces'))
        self.assertFalse(self.engine.verifyUrlSection('url with-space'))
        # idk...
        
    def test_getClientIp(self):
        class FakeRequest(object):
            def __init__(self):
                class FakeEnviron(object):
                    def get(self, s):
                        if s == 'REMOTE_ADDR':
                            return '1.2.3.4'
                        else:
                            return '5.6.7.8'
                self.environ = FakeEnviron()
        
        dummy_request = FakeRequest()
        self.assertEqual(self.engine.getClientIp(dummy_request), '1.2.3.4')
        
        # reload engine with unix socket  
        settings = EngineTest.defaultSettings()
        settings['hosting']['socket'] = '/path/to/socket' 
        self.reloadEngine(settings=settings)
        self.assertEqual(self.engine.getClientIp(dummy_request), '5.6.7.8')

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
        self.assertEqual(self.engine.getClientAgent(dummy_request), 'Fake Browser')
        
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
            ret = self.engine.getMd5(h)
            self.assertIsInstance(ret, str)
        
    def test_getSize(self):
        # create dummy file
        with tempfile.TemporaryFile() as h:
            h.write(b'0' * 4953)
            
            # rewind for reading
            h.seek(0)
            fupload = FileUpload(h, 'demo.dat', 'demo.dat')
            size = self.engine.getSize(fupload)
            self.assertEqual(size, 4953)
        
    def test_getSupportedDice(self):
        dice = self.engine.getSupportedDice()
        self.assertEqual(dice, [2, 4, 6, 8, 10, 12, 20, 100])
        
    def test_cleanup(self):
        now = time.time()
        
        with db_session:
            # create GMs
            gm1 = self.engine.main_db.GM(name='user123', url='url456', sid='123456')
            gm1.postSetup()
            gm2 = self.engine.main_db.GM(name='nobody', url='second', sid='5673')
            gm2.postSetup()
            gm2.timeid = now - self.engine.expire - 10
        
        gm1_cache = self.engine.cache.get(gm1)
        gm1_cache.connect_db()
        gm2_cache = self.engine.cache.get(gm2)
        gm2_cache.connect_db()
        
        with db_session:
            # create some games
            g1 = gm1_cache.db.Game(url='foo', gm_url='url456')
            g1.postSetup()
            g2 = gm1_cache.db.Game(url='bar', gm_url='url456')
            g2.timeid = time.time() - self.engine.expire - 10
            g2.postSetup()
            
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
            g1.toZip()
            g2.toZip()
            export_path = self.engine.paths.getExportPath()
            num_files = len(os.listdir(export_path))
            self.assertEqual(num_files, 2)
            
            # cleanup!
            self.engine.cleanup()
            
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
            gm1 = self.engine.main_db.GM(name='user123', url='url456', sid='123456')
            gm1.postSetup()
            gm2 = self.engine.main_db.GM(name='nobody', url='second', sid='5673')
            gm2.postSetup()
        
        gm1_cache = self.engine.cache.get(gm1)
        gm1_cache.connect_db()
        gm2_cache = self.engine.cache.get(gm2)
        gm2_cache.connect_db()
        
        with db_session:
            # create some games
            g1 = gm1_cache.db.Game(url='foo', gm_url='second')
            g1.postSetup()
            g2 = gm1_cache.db.Game(url='bar', gm_url='second')
            g2.timeid = time.time() - self.engine.expire - 10
            g2.postSetup()
            g3 = gm2_cache.db.Game(url='bar', gm_url='url456')
            g3.timeid = time.time() - self.engine.expire - 10
            g3.postSetup()

        export = self.engine.saveToDict()

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
            'games': {
                'test': {
                    'tokens': [{'url': 5, 'posx': 12, 'posy': 34, 'zorder': 56, 'size': 120, 'rotate': 22.5, 'flipx': True, 'locked': True}],
                    'scenes': [{'tokens': [0], 'backing': None}]
                }
            }
        }]

        self.engine.loadFromDict(data)

        # check GM data
        with db_session:
            all_gms = list(self.engine.main_db.GM.select())
        self.assertEqual(len(all_gms), 1)
        self.assertEqual(all_gms[0].name, 'otto')
        self.assertEqual(all_gms[0].url,  '12345')
        self.assertEqual(all_gms[0].sid,  'foobar1234')

        # check Games Data
        gm_cache = self.engine.cache.getFromUrl('12345')
        with db_session:
            all_games = list(gm_cache.db.Game.select())
        self.assertEqual(len(all_games), 1)



