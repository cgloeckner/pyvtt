#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import tempfile, json, os, zipfile, gevent, requests, shutil

from PIL import Image

import vtt

from test.utils import EngineBaseTest, SocketDummy



def makeImage(w, h):
    pil_img = Image.new(mode='RGB', size=(w, h))
    with tempfile.NamedTemporaryFile('wb') as wh:
        pil_img.save(wh.name, 'BMP')
        with open(wh.name, 'rb') as rh:
            return rh.read()

def makeZip(fname, data, n):
    with tempfile.TemporaryDirectory() as tmp_dir:
        # create json
        json_path = os.path.join(tmp_dir, 'game.json')
        with open(json_path , 'w') as jh:
            jh.write(data)
        # create image
        for i in range(n):         
            img_path = os.path.join(tmp_dir, '{0}.bmp'.format(i))
            img_file = Image.new(mode='RGB', size=(1024, 1024))
            img_file.save(img_path)
        # pack zip
        zip_path = os.path.join(tmp_dir, '{0}.zip'.format(fname))
        with zipfile.ZipFile(zip_path, "w") as zh:
            zh.write(json_path, 'game.json')
            for i in range(n):  
                zh.write(img_path, '{0}.bmp'.format(i))
        with open(zip_path, 'rb') as rh:
            return rh.read()


# ---------------------------------------------------------------------

class VttTest(EngineBaseTest):

    def setUp(self):
        super().setUp()        
        vtt.setup_resource_routes(self.engine)
        vtt.setup_gm_routes(self.engine)
        vtt.setup_player_routes(self.engine)
        # @NOTE: custom errorpages are not routed here
    
    def test_get_root(self):
        # expect redirect to login
        ret = self.app.get('/')
        self.assertEqual(ret.status_int, 302)
        self.assertEqual(ret.location, 'http://localhost:80/vtt/join')
        ret = ret.follow() 
        self.assertEqual(ret.status_int, 200)
        ret = self.app.get('/')

        # expect games menu if logged in
        ret = self.app.post('/vtt/join', {'gmname': 'arthur'}, xhr=True)
        self.assertEqual(ret.status_int, 200)
        ret = self.app.get('/')
        self.assertEqual(ret.status_int, 200)

        # expect redirect if a session ID is faked
        self.app.set_cookie('session', 'randomstuffthatisnotasessionid')
        ret = self.app.get('/')
        self.assertEqual(ret.status_int, 302)
        self.assertEqual(self.app.cookies['session'], '""')

    
    # -----------------------------------------------------------------
    
    def joinPlayer(self, gm_url, game_url, playername, playercolor):
        # post login
        ret = self.app.post('/{0}/{1}/login'.format(gm_url, game_url),
            {'playername': playername, 'playercolor': playercolor})
        self.assertEqual(ret.status_int, 200)
        # open fake socket
        s = SocketDummy()
        s.block = True
        s.push_receive({'name': playername, 'gm_url': gm_url, 'game_url': game_url})
        # listen to the faked websocket
        return ret, self.engine.cache.listen(s)
    

    # -----------------------------------------------------------------

    def test_get_vtt_patreon_callback(self):
        # expect 404 because engine is loaded without patreon support
        # hence callback is not used in that case
        ret = self.app.get('/vtt/patreon/callback', expect_errors=True)
        self.assertEqual(ret.status_int, 404)
    
    def test_get_vtt_join(self):
        ret = self.app.get('/vtt/join')
        self.assertEqual(ret.status_int, 200)

    def test_post_vtt_join(self):
        # @NOTE: this route is working because the engine was loaded
        # without patreon-support, hence GMs can create an account
        # directly

        # can create a GM account
        args = {
            'gmname' : 'arthur'
        }
        ret = self.app.post('/vtt/join', args, xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'application/json')
        # expect json response
        self.assertEqual(ret.json['error'], '')
        self.assertEqual(ret.json['url'], args['gmname'])
        self.assertIn('session', self.app.cookies)
        
        # cannot create GM with name collision             
        self.app.reset()
        ret = self.app.post('/vtt/join', args, xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'application/json')
        self.assertEqual(ret.json['error'], 'ALREADY IN USE')
        self.assertIsNone(ret.json['url'])
        self.assertNotIn('session', self.app.cookies)
        
        # can create GM but name is cut
        self.app.reset()
        args = {
            'gmname' : 'arthurhasaverylongnamethatiscutafter20chars'
        } 
        ret = self.app.post('/vtt/join', args, xhr=True)
        self.assertEqual(ret.status_int, 200) 
        self.assertEqual(ret.content_type, 'application/json')
        self.assertEqual(ret.json['error'], '')
        self.assertEqual(ret.json['url'], args['gmname'][:20])
        self.assertIn('session', self.app.cookies)

        # cannot create GM with invalid name
        for name in ['king\arthur', 'king arthur', 'king?arthur']: 
            self.app.reset()
            ret = self.app.post('/vtt/join', {'gmname': name}, xhr=True)
            self.assertEqual(ret.status_int, 200)             
            self.assertEqual(ret.content_type, 'application/json')
            self.assertEqual(ret.json['error'], 'NO SPECIAL CHARS OR SPACES')
            self.assertIsNone(ret.json['url'])
            self.assertNotIn('session', self.app.cookies)

        # cannot create GM with blacklisted name        
        self.app.reset()
        ret = self.app.post('/vtt/join', {'gmname': 'vtt'}, xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'application/json')
        self.assertEqual(ret.json['error'], 'RESERVED NAME')
        self.assertEqual(ret.json['url'], None)
        self.assertNotIn('session', self.app.cookies)
    
    def test_vtt_fancyurl(self):
        ret = self.app.get('/vtt/fancy-url')
        self.assertEqual(ret.status_int, 200)  
        self.assertEqual(ret.content_type, 'text/html')
        # expect 3 words separated with 2 '-'
        fancy_url = ret.unicode_normal_body
        self.assertEqual(len(fancy_url.split('-')), 3)
        for word in fancy_url.split('-'):
            self.assertNotEqual(word, '')

    def test_vtt_importgame(self):
        # create some images
        img_small = makeImage(512, 512)
        img_large = makeImage(1500, 1500)
        img_huge  = makeImage(2000, 2000)
        mib = 2**20
        self.assertLess(len(img_small), mib)       
        self.assertLess(len(img_large), (self.engine.file_limit['background']+1) * mib)
        self.assertGreater(len(img_large), (self.engine.file_limit['background'] // 2) * mib)  
        self.assertGreater(len(img_huge), self.engine.file_limit['background'] * mib)

        # create some zips
        empty_game = json.dumps({
            'tokens': [],
            'scenes': [{'tokens': [], 'backing': None}]
        })
        
        zip_normal = makeZip('zip2', empty_game, 5)
        zip_huge   = makeZip('zip2', empty_game, self.engine.file_limit['game'])
        self.assertLess(len(zip_normal), self.engine.file_limit['game'] * mib)
        self.assertGreater(len(zip_huge), self.engine.file_limit['game'] * mib)
        
        fake_file = b'0' * mib
        text_file = b'hello world'

        # register
        ret = self.app.post('/vtt/join', {'gmname': 'arthur'}, xhr=True)
        self.assertEqual(ret.status_int, 200)
        sid = self.app.cookies['session']

        # reset app to clear cookies
        self.app.reset()

        # cannot import image without GM session
        ret = self.app.post('/vtt/import-game/',
            upload_files=[('file', 'test.png', img_small)], xhr=True, expect_errors=True)
        self.assertEqual(ret.status_int, 404)

        # cannot import zip without GM session
        ret = self.app.post('/vtt/import-game/',
            upload_files=[('file', 'test.zip', img_small)], xhr=True, expect_errors=True)
        self.assertEqual(ret.status_int, 404)

        self.app.set_cookie('session', 'something-that-shall-fake-a-session')
        
        # cannot import image without valid GM session
        ret = self.app.post('/vtt/import-game/',
            upload_files=[('file', 'test.png', img_small)], xhr=True, expect_errors=True)
        self.assertEqual(ret.status_int, 404)

        # cannot import zip without valid GM session
        ret = self.app.post('/vtt/import-game/',
            upload_files=[('file', 'test.zip', img_small)], xhr=True, expect_errors=True)
        self.assertEqual(ret.status_int, 404)

        # login again
        self.app.set_cookie('session', sid)
        
        # can import image with auto-url 
        ret = self.app.post('/vtt/import-game/',
            upload_files=[('file', 'test.png', img_small)], xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'application/json')
        self.assertTrue(ret.json['url_ok'])
        self.assertTrue(ret.json['file_ok'])
        self.assertEqual(ret.json['error'], '')
        self.assertEqual(len(ret.json['url'].split('/')), 2)
        self.assertEqual(ret.json['url'].split('/')[0], 'arthur')
        self.assertNotEqual(ret.json['url'].split('/')[1], 'arthur')
        
        # can import image with custom url (ignoring cases)
        ret = self.app.post('/vtt/import-game/teSt-uRL-1',
            upload_files=[('file', 'test.png', img_small)], xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'application/json')
        self.assertTrue(ret.json['url_ok'])
        self.assertTrue(ret.json['file_ok'])
        self.assertEqual(ret.json['error'], '')
        self.assertEqual(ret.json['url'], 'arthur/test-url-1')
        ret = self.app.get('/arthur/test-url-1')
        self.assertEqual(ret.status_int, 200)
        
        # cannot use custom url twice
        ret = self.app.post('/vtt/import-game/test-url-1',
            upload_files=[('file', 'test.png', img_small)], xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'application/json')
        self.assertFalse(ret.json['url_ok'])
        self.assertEqual(ret.json['error'], 'ALREADY IN USE')
        self.assertEqual(ret.json['url'], '')
        
        # can import image with very long custom url
        ret = self.app.post('/vtt/import-game/test-url-1-but-this-time-with-way-more-than-30-chars-total',
            upload_files=[('file', 'test.png', img_small)], xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'application/json')
        self.assertTrue(ret.json['url_ok'])
        self.assertTrue(ret.json['file_ok'])
        self.assertEqual(ret.json['error'], '')
        self.assertEqual(ret.json['url'], 'arthur/test-url-1-but-this-time-with-')
        ret = self.app.get('/arthur/test-url-1-but-this-time-with-')
        self.assertEqual(ret.status_int, 200)
        
        # cannot import image with invalid url
        ret = self.app.post('/vtt/import-game/test url-2',
            upload_files=[('file', 'test.png', img_small)], xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'application/json')   
        self.assertEqual(ret.json['error'], 'NO SPECIAL CHARS OR SPACES')
        self.assertEqual(ret.json['url'], '')
        self.assertFalse(ret.json['url_ok'])   
        ret = self.app.get('/arthur/test url-2', expect_errors=True)
        self.assertEqual(ret.status_int, 404)
        
        # cannot import multiple files at once
        ret = self.app.post('/vtt/import-game/test-url-3',
            upload_files=[
                ('file', 'test.png', img_small),
                ('file', 'test.png', img_small)
            ], xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'application/json') 
        self.assertTrue(ret.json['url_ok'])
        self.assertFalse(ret.json['file_ok'])
        self.assertEqual(ret.json['error'], 'ONE FILE AT ONCE')
        ret = self.app.get('/arthur/test-url-3', expect_errors=True)
        self.assertEqual(ret.status_int, 404)
        
        # can upload large background
        ret = self.app.post('/vtt/import-game/test-url-4',
            upload_files=[('file', 'test.png', img_large)], xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'application/json')
        self.assertTrue(ret.json['url_ok'])
        self.assertTrue(ret.json['file_ok'])
        self.assertEqual(ret.json['error'], '')
        self.assertEqual(ret.json['url'], 'arthur/test-url-4')
        ret = self.app.get('/arthur/test-url-4')
        self.assertEqual(ret.status_int, 200)
            
        # cannot upload too large background
        ret = self.app.post('/vtt/import-game/test-url-5',
            upload_files=[('file', 'test.png', img_huge)], xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'application/json')
        self.assertTrue(ret.json['url_ok'])
        self.assertFalse(ret.json['file_ok'])
        self.assertEqual(ret.json['error'], 'TOO LARGE BACKGROUND (MAX {0} MiB)'.format(self.engine.file_limit['background']))
        self.assertEqual(ret.json['url'], '')
        ret = self.app.get('/arthur/test-url-5', expect_errors=True)
        self.assertEqual(ret.status_int, 404)
        
        # cannot upload a fake zip file
        ret = self.app.post('/vtt/import-game/test-url-6',
            upload_files=[('file', 'test.zip', fake_file)], xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'application/json')
        self.assertTrue(ret.json['url_ok'])
        self.assertFalse(ret.json['file_ok'])
        self.assertEqual(ret.json['error'], 'CORRUPTED FILE')   
        self.assertEqual(ret.json['url'], '')
        ret = self.app.get('/arthur/test-url-6', expect_errors=True)
        self.assertEqual(ret.status_int, 404)
        
        # can upload zip file
        ret = self.app.post('/vtt/import-game/test-url-7',
            upload_files=[('file', 'test.zip', zip_normal)], xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'application/json')
        self.assertTrue(ret.json['url_ok'])
        self.assertTrue(ret.json['file_ok'])
        self.assertEqual(ret.json['error'], '')
        ret = self.app.get('/arthur/test-url-7')
        self.assertEqual(ret.status_int, 200)
        
        # cannot upload too large zip file
        ret = self.app.post('/vtt/import-game/test-url-8',
            upload_files=[('file', 'test.zip', zip_huge)], xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'application/json')
        self.assertTrue(ret.json['url_ok'])
        self.assertFalse(ret.json['file_ok'])
        self.assertEqual(ret.json['error'], 'TOO LARGE GAME (MAX {0} MiB)'.format(self.engine.file_limit['game']))
        ret = self.app.get('/arthur/test-url-8', expect_errors=True)
        self.assertEqual(ret.status_int, 404)
        
        # cannot upload any other file format
        ret = self.app.post('/vtt/import-game/test-url-9',
            upload_files=[('file', 'test.txt', text_file)], xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'application/json')
        self.assertTrue(ret.json['url_ok'])
        self.assertFalse(ret.json['file_ok'])
        self.assertEqual(ret.json['error'], 'USE AN IMAGE FILE')
        self.assertEqual(ret.json['url'], '')  
        ret = self.app.get('/arthur/test-url-9', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_exportgame(self):
        # register arthur
        ret = self.app.post('/vtt/join', {'gmname': 'arthur'}, xhr=True)
        self.assertEqual(ret.status_int, 200)
        arthur_sid = self.app.cookies['session']
        
        # create a game 
        img_small = makeImage(512, 512)
        ret = self.app.post('/vtt/import-game/test-exportgame-1',
            upload_files=[('file', 'test.png', img_small)], xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'application/json')
        self.assertTrue(ret.json['url_ok'])
        self.assertTrue(ret.json['file_ok'])
        self.assertEqual(ret.json['error'], '')
        self.assertEqual(ret.json['url'], 'arthur/test-exportgame-1')

        # register bob
        ret = self.app.post('/vtt/join', {'gmname': 'bob'}, xhr=True)
        self.assertEqual(ret.status_int, 200)
        bob_sid = self.app.cookies['session']
        
        # create a game 
        img_small = makeImage(512, 512)
        ret = self.app.post('/vtt/import-game/this-one-is-bob',
            upload_files=[('file', 'test.png', img_small)], xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'application/json')
        self.assertTrue(ret.json['url_ok'])
        self.assertTrue(ret.json['file_ok'])
        self.assertEqual(ret.json['error'], '')
        self.assertEqual(ret.json['url'], 'bob/this-one-is-bob')

        # reset app to clear cookies
        self.app.reset()
        
        # cannot export game without GM session
        ret = self.app.get('/vtt/export-game/test-exportgame-1', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

        self.app.set_cookie('session', 'something-that-shall-fake-a-session')
        
        # cannot export game without valid GM session
        ret = self.app.get('/vtt/export-game/test-exportgame-1', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

        # login as arthur
        self.app.set_cookie('session', arthur_sid)
        
        # can export existing game
        ret = self.app.get('/vtt/export-game/test-exportgame-1')
        self.assertEqual(ret.status_int, 200)
        
        # can export another GM's game
        ret = self.app.get('/vtt/export-game/this-one-is-bob', expect_errors=True)
        self.assertEqual(ret.status_int, 404)
        
        # cannot export unknown game
        ret = self.app.get('/vtt/export-game/test-anything-else', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_vtt_cleanup(self):
        # register arthur
        ret = self.app.post('/vtt/join', {'gmname': 'arthur'}, xhr=True)
        self.assertEqual(ret.status_int, 200)
        
        # create a game 
        img_small = makeImage(512, 512)
        ret = self.app.post('/vtt/import-game/test-game-1',
            upload_files=[('file', 'test.png', img_small)], xhr=True)
        self.assertEqual(ret.status_int, 200)
        gm_sid = self.app.cookies['session']
        self.app.reset()

        # let players join and start (faked) websocket
        ret1, player1 = self.joinPlayer('arthur', 'test-game-1', 'arthur', 'gold')
        ret2, player2 = self.joinPlayer('arthur', 'test-game-1', 'bob', 'red')
        ret3, player3 = self.joinPlayer('arthur', 'test-game-1', 'carlos', 'blue')

        gm_cache   = self.engine.cache.getFromUrl('arthur')
        game_cache = gm_cache.getFromUrl('test-game-1')
        self.assertEqual(len(game_cache.players), 3)

        # non-GM cannot cleanup
        ret = self.app.post('/vtt/clean-up/test-game-1', expect_errors=True)
        self.assertEqual(ret.status_int, 404)
        self.assertEqual(len(game_cache.players), 3)
        
        # GM cannot cleanup for unknown game
        self.app.set_cookie('session', gm_sid)
        ret = self.app.post('/vtt/clean-up/test-weird', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

        # upload some music
        ret = self.app.post('/arthur/test-game-1/upload',
            upload_files=[('file[]', 'sample.mp3', b'')], xhr=True)
        
        # GM can cleanup his game
        self.app.set_cookie('session', gm_sid)
        ret = self.app.post('/vtt/clean-up/test-game-1')
        self.assertEqual(ret.status_int, 200)
        # expect music websockets to contain music refresh action

    def test_vtt_kickplayer(self):
        # register arthur
        ret = self.app.post('/vtt/join', {'gmname': 'arthur'}, xhr=True)
        self.assertEqual(ret.status_int, 200)
        
        # create a game 
        img_small = makeImage(512, 512)
        ret = self.app.post('/vtt/import-game/test-game-1',
            upload_files=[('file', 'test.png', img_small)], xhr=True)
        self.assertEqual(ret.status_int, 200)
        gm_sid = self.app.cookies['session']
        self.app.reset()

        # let players join and start (faked) websocket
        ret1, player1 = self.joinPlayer('arthur', 'test-game-1', 'arthur', 'gold')
        ret2, player2 = self.joinPlayer('arthur', 'test-game-1', 'bob', 'red')
        ret3, player3 = self.joinPlayer('arthur', 'test-game-1', 'carlos', 'blue')
        ret3, player4 = self.joinPlayer('arthur', 'test-game-1', 'blocker', 'green')

        gm_cache   = self.engine.cache.getFromUrl('arthur')
        game_cache = gm_cache.getFromUrl('test-game-1')
        self.assertEqual(len(game_cache.players), 4) 
        
        # non-GM cannot kick any player
        for p in [player1, player2, player3]:
            ret = self.app.post('/vtt/kick-player/test-game-1/{0}'.format(p.uuid), expect_errors=True)
            self.assertEqual(ret.status_int, 404)
            self.assertEqual(len(game_cache.players), 4)
        
        # GM cannot kick players from unknown game
        self.app.set_cookie('session', gm_sid)
        for p in [player1, player2, player3]:
            ret = self.app.post('/vtt/kick-player/test-weird-1/{0}'.format(p.uuid), expect_errors=True)
            self.assertEqual(ret.status_int, 404)
            self.assertEqual(len(game_cache.players), 4)
        
        # GM can kick a single player from his game
        self.app.set_cookie('session', gm_sid)
        ret = self.app.post('/vtt/kick-player/test-game-1/{0}'.format(player2.uuid))
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(len(game_cache.players), 3)
        self.assertIn('arthur', game_cache.players) 
        self.assertNotIn('bob', game_cache.players)
        self.assertIn('carlos', game_cache.players)
        gevent.kill(player2.greenlet)
        
        # GM can himself from his game
        self.app.set_cookie('session', gm_sid)
        ret = self.app.post('/vtt/kick-player/test-game-1/{0}'.format(player1.uuid))
        self.assertEqual(ret.status_int, 200) 
        self.assertEqual(len(game_cache.players), 2)
        self.assertNotIn('arthur', game_cache.players)
        self.assertIn('carlos', game_cache.players) 
        gevent.kill(player1.greenlet)

        # GM can even kick a player if when offline
        self.app.set_cookie('session', gm_sid)
        ret = self.app.post('/vtt/kick-player/test-game-1/{0}'.format(player3.uuid))
        self.assertEqual(ret.status_int, 200) 
        self.assertEqual(len(game_cache.players), 1) 
        gevent.kill(player2.greenlet)
        
        # GM cannot kick player twice (but nothing happens)
        self.app.set_cookie('session', gm_sid)
        ret = self.app.post('/vtt/kick-player/test-game-1/{0}'.format(player3.uuid))
        self.assertEqual(ret.status_int, 200) 
        self.assertEqual(len(game_cache.players), 1)
        
    def test_vtt_deletegame(self):
        # register arthur
        ret = self.app.post('/vtt/join', {'gmname': 'arthur'}, xhr=True)
        self.assertEqual(ret.status_int, 200)
        
        # create a game 
        img_small = makeImage(512, 512)
        ret = self.app.post('/vtt/import-game/test-game-1',
            upload_files=[('file', 'test.png', img_small)], xhr=True)
        self.assertEqual(ret.status_int, 200)
        gm_sid = self.app.cookies['session']
        self.app.reset()

        gm_cache = self.engine.cache.getFromUrl('arthur')
        
        # non-GM cannot delete the game
        ret = self.app.post('/vtt/delete-game/test-game-1', expect_errors=True)
        self.assertEqual(ret.status_int, 404)
        self.assertIsNotNone(gm_cache.getFromUrl('test-game-1'))
        
        # GM cannot delete an unknown game
        self.app.set_cookie('session', gm_sid)
        ret = self.app.post('/vtt/delete-game/test-weird-game', expect_errors=True)
        self.assertEqual(ret.status_int, 404)
        self.assertIsNotNone(gm_cache.getFromUrl('test-game-1'))
        
        # GM can delete a game
        ret = self.app.post('/vtt/delete-game/test-game-1')
        self.assertEqual(ret.status_int, 200)
        self.assertIsNone(gm_cache.getFromUrl('test-game-1'))
        
        # GM cannot delete a game twice
        ret = self.app.post('/vtt/delete-game/test-game-1', expect_errors=True)
        self.assertEqual(ret.status_int, 404)
    
    def test_vtt_queryscenes(self):
        # register arthur
        ret = self.app.post('/vtt/join', {'gmname': 'arthur'}, xhr=True)
        self.assertEqual(ret.status_int, 200)
        
        # create a game 
        img_small = makeImage(512, 512)
        ret = self.app.post('/vtt/import-game/test-game-1',
            upload_files=[('file', 'test.png', img_small)], xhr=True)
        self.assertEqual(ret.status_int, 200)
        gm_sid = self.app.cookies['session']
        self.app.reset()

        # create some scenes
        gm_ret, gm_player = self.joinPlayer('arthur', 'test-game-1', 'arthur', 'gold')
        for i in range(3):
            gm_player.socket.push_receive({'OPID': 'GM-CREATE'})
        
        # non-GM cannot query scenes
        ret = self.app.post('/vtt/query-scenes/test-game-1', expect_errors=True)
        self.assertEqual(ret.status_int, 404)
        
        # GM cannot query scenes from unknown game
        self.app.set_cookie('session', gm_sid)
        ret = self.app.post('/vtt/query-scenes/test-weird-game', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

        # GM can query scenes from a game
        ret = self.app.post('/vtt/query-scenes/test-game-1')
        self.assertEqual(ret.status_int, 200)

    def test_vtt_queryurl(self):
        # register arthur
        ret = self.app.post('/vtt/join', {'gmname': 'arthur'}, xhr=True)
        self.assertEqual(ret.status_int, 200)
        
        # create a game 
        img_small = makeImage(512, 512)
        ret = self.app.post('/vtt/import-game/test-game-1',
            upload_files=[('file', 'test.png', img_small)], xhr=True)
        self.assertEqual(ret.status_int, 200)
        gm_sid = self.app.cookies['session']
        self.app.reset()

        # create some scenes
        gm_ret, gm_player = self.joinPlayer('arthur', 'test-game-1', 'arthur', 'gold')
        for i in range(3):
            gm_player.socket.push_receive({'OPID': 'GM-CREATE'})
        
        # non-GM can query for missing url
        ret = self.app.get('/vtt/query-url/arthur/test-game-1/foobar', expect_errors=True)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.body, b'')
    
    def test_vtt_status(self):
        # can query if no more shards were specified
        ret = self.app.get('/vtt/status', expect_errors=True)
        self.assertEqual(ret.status_int, 200)

        # can query if shard was set up
        self.engine.shards = ['http://localhost:80']
        ret = self.app.get('/vtt/status')
        self.assertEqual(ret.status_int, 200)
        # @NOTE: this needs to be rewritten, since there's no `ps` in slim containres
        """
        self.assertIn('cpu', ret.json)
        self.assertIn('memory', ret.json)
        """
        self.assertIn('num_players', ret.json)
        
    def test_vtt_query(self):
        # can only query this server if no shards are specified
        ret = self.app.get('/vtt/query/0', expect_errors=True)
        self.assertEqual(ret.status_int, 200)
        
        # setup server shards
        test_ports = [8081, 8000]
        servers = [self]
        self.engine.shards = ['http://localhost:{0}'.format(p) for p in test_ports]
        self.engine.shards.append('http://localhost:80') # this server
        greenlets = list()
        for port in test_ports:
            # confirm port to be free
            with self.assertRaises(requests.exceptions.ConnectionError):
                requests.get('http://localhost:{0}'.format(port))
            # setup server instance
            e = EngineBaseTest()
            e.setUp()
            e.engine.hosting['port'] = port
            e.engine.shards = self.engine.shards
            # run in thread
            g = gevent.Greenlet(run=e.engine.run)
            g.start()
            greenlets.append(g)
            # confirm server is online
            requests.get('http://localhost:{0}'.format(port))

        # can query all servers
        for i, url in enumerate(self.engine.shards):
            ret = self.app.get('/vtt/query/{0}'.format(i))
            self.assertEqual(ret.status_int, 200)
            # @NOTE: cannot test countryCode due to localhost and status
            # because this may fail on the github workflow test
        
        # cannot query unknown server
        ret = self.app.get('/vtt/query/245245', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

        # stop server shard instances
        for g in greenlets:
            gevent.kill(g)
        
    def test_vtt_shard(self):
        # can show shards page if no more shards were specified
        ret = self.app.get('/vtt/shard', expect_errors=True)
        self.assertEqual(ret.status_int, 200)

        # can show shard page for single server
        self.engine.shards = ['http://localhost:80']
        ret = self.app.get('/vtt/shard')
        self.assertEqual(ret.status_int, 200)
        
        # can show shard page for many servers
        self.engine.shards = ['https://{0}'.format(h) for h in ['example.com', 'foo.bar', 'test.org']]
        ret = self.app.get('/vtt/shard')
        self.assertEqual(ret.status_int, 200)
    
    def test_static_fname(self):
        # cannot query non existing files
        ret = self.app.get('/static/fantasy-file.txt', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

        # can query existing images
        ret = self.app.get('/static/d20.png')
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'image/png')
        
        ret = self.app.get('/static/background.jpg')
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'image/jpeg')
        
        ret = self.app.get('/static/favicon.ico')
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'image/vnd.microsoft.icon')
        
        # can query existing javascript files
        ret = self.app.get('/static/render.js')
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'application/javascript')
        
        # can query existing css files
        ret = self.app.get('/static/layout.css')
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'text/css')

        # cannot query parent directory   
        ret = self.app.get('/static/../README.md/0', expect_errors=True)  
        self.assertEqual(ret.status_int, 404)

        # cannot query sub-directory
        tmp_static = self.root / 'static'
        if not os.path.exists(tmp_static):
            os.mkdir(tmp_static)
        sub_dir = tmp_static / 'test'
        if not os.path.exists(sub_dir):
            os.mkdir(sub_dir)
        with open(sub_dir / 'test.txt', 'w') as h:
            h.write('hello world')
        ret = self.app.get('/static/sub/test.txt', expect_errors=True)  
        self.assertEqual(ret.status_int, 404)

    def test_token_fname(self):
        # register arthur
        ret = self.app.post('/vtt/join', {'gmname': 'arthur'}, xhr=True)
        self.assertEqual(ret.status_int, 200)
        
        # create two games
        img_small = makeImage(512, 512)
        ret = self.app.post('/vtt/import-game/test-game-1',
            upload_files=[('file', 'test.png', img_small)], xhr=True) 
        self.assertEqual(ret.status_int, 200)
        ret = self.app.post('/vtt/import-game/test-game-2',
            upload_files=[('file', 'test.png', img_small)], xhr=True)
        self.assertEqual(ret.status_int, 200)
        gm_sid = self.app.cookies['session']
        self.app.reset()

        # create more images
        img_path = self.engine.paths.getGamePath('arthur', 'test-game-1')
        shutil.copyfile(img_path / '0.png', img_path / '1.png')

        # can query this image
        ret = self.app.get('/token/arthur/test-game-1/0.png')
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'image/png')
        ret = self.app.get('/token/arthur/test-game-1/1.png')
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'image/png')

        # cannot query unknown image (within right game)
        ret = self.app.get('/token/arthur/test-game-2/2.png', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

        # cannot query image from another game
        ret = self.app.get('/token/arthur/test-game-2/0.png')
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'image/png')
        
        # cannot query image from unknown game
        ret = self.app.get('/token/arthur/test-game-3/0.png', expect_errors=True)
        self.assertEqual(ret.status_int, 404)
        
        # cannot query image from unknown gm
        ret = self.app.get('/token/carlos/test-game-3/0.png', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

        # cannot query GM's database         
        ret = self.app.get('/token/arthur/test-game-1/../gm.db', expect_errors=True)
        self.assertEqual(ret.status_int, 404)
        ret = self.app.get('/token/arthur/test-game-1/../&#47;m.db', expect_errors=True)
        self.assertEqual(ret.status_int, 404)
        ret = self.app.get('/token/arthur/../gm.db', expect_errors=True)
        self.assertEqual(ret.status_int, 404)
        ret = self.app.get('/token/arthur/test-game-1/"../gm.db"', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

        # cannot query non-image files
        with open(img_path / 'test.txt', 'w') as h:
            h.write('hello world') 
        ret = self.app.get('/token/arthur/test-game-1/test.txt', expect_errors=True)
        self.assertEqual(ret.status_int, 404)
    
    def test_game_screen(self):
        # register arthur
        ret = self.app.post('/vtt/join', {'gmname': 'arthur'}, xhr=True)
        self.assertEqual(ret.status_int, 200)
        
        # create a game
        img_small = makeImage(512, 512)
        ret = self.app.post('/vtt/import-game/test-game-1',
            upload_files=[('file', 'test.png', img_small)], xhr=True)
        self.assertEqual(ret.status_int, 200)
        gm_sid = self.app.cookies['session']
        self.app.reset()

        # can access login screen for existing game
        ret = self.app.get('/arthur/test-game-1')
        self.assertEqual(ret.status_int, 200)
        # expect GM dropdown NOT to be loaded
        self.assertNotIn('onClick="addScene();"', ret.unicode_normal_body)
        
        # cannot access unknown game
        ret = self.app.get('/arthur/test-game-2', expect_errors=True)
        self.assertEqual(ret.status_int, 404)
        
        # cannot access unknown GM's
        ret = self.app.get('/bob/test-game-2', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

        # can access as GM
        self.app.set_cookie('session', gm_sid)
        ret = self.app.get('/arthur/test-game-1')
        self.assertEqual(ret.status_int, 200)
        # expect GM dropdown to be loaded
        self.assertIn('onClick="addScene();"', ret.unicode_normal_body)
        
    def test_game_login(self):
        # register arthur
        ret = self.app.post('/vtt/join', {'gmname': 'arthur'}, xhr=True)
        self.assertEqual(ret.status_int, 200)
        
        # create a game
        img_small = makeImage(512, 512)
        ret = self.app.post('/vtt/import-game/test-game-1',
            upload_files=[('file', 'test.png', img_small)], xhr=True)
        self.assertEqual(ret.status_int, 200)
        gm_sid = self.app.cookies['session']
        self.app.reset()

        # players can login (with a fake socket)
        ret1, player1 = self.joinPlayer('arthur', 'test-game-1', 'bob', 'red')
        self.assertEqual(ret1.status_int, 200)
        self.assertNotEqual(ret1.json['uuid'], '')
        self.assertEqual(ret1.json['error'], '')
        self.assertFalse(ret1.json['is_gm'])
        self.assertEqual(ret1.json['playername'], 'bob')
        self.assertEqual(ret1.json['playercolor'], 'red')
        ret2, player2 = self.joinPlayer('arthur', 'test-game-1', 'carlos', 'blue')
        self.assertEqual(ret2.status_int, 200)  
        self.assertNotEqual(ret2.json['uuid'], '')
        self.assertFalse(ret2.json['is_gm'])
        self.assertEqual(ret2.json['error'], '')
        self.assertEqual(ret2.json['playername'], 'carlos')
        self.assertEqual(ret2.json['playercolor'], 'blue')

        # player cannot login with the same name
        ret = self.app.post('/arthur/test-game-1/login', {'playername': 'carlos', 'playercolor': 'blue'})
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.json['uuid'], '')
        self.assertFalse(ret.json['is_gm'])
        self.assertEqual(ret.json['error'], 'ALREADY IN USE')
        self.assertEqual(ret.json['playername'], '')
        self.assertEqual(ret.json['playercolor'], '')
        
        # player cannot name
        ret = self.app.post('/arthur/test-game-1/login', {'playername': '', 'playercolor': 'blue'})
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.json['uuid'], '')
        self.assertFalse(ret.json['is_gm'])
        self.assertEqual(ret.json['error'], 'PLEASE ENTER A NAME')
        self.assertEqual(ret.json['playername'], '')
        self.assertEqual(ret.json['playercolor'], '')
        
        # player cannot login to unknown game
        ret = self.app.post('/arthur/test-game-2/login', {'playername': 'dagmar', 'playercolor': 'black'})
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.json['uuid'], '')
        self.assertFalse(ret.json['is_gm'])
        self.assertEqual(ret.json['error'], 'GAME NOT FOUND')
        self.assertEqual(ret.json['playername'], '')
        self.assertEqual(ret.json['playercolor'], '')
        
        # player cannot login to unknown GM's game
        ret = self.app.post('/horatio/test-game-1/login', {'playername': 'dagmar', 'playercolor': 'black'})
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.json['uuid'], '')
        self.assertFalse(ret.json['is_gm'])
        self.assertEqual(ret.json['error'], 'GAME NOT FOUND')
        self.assertEqual(ret.json['playername'], '')
        self.assertEqual(ret.json['playercolor'], '')

        # player can login after being kicked
        self.app.set_cookie('session', gm_sid)
        ret = self.app.post('/vtt/kick-player/test-game-1/{0}'.format(player2.uuid))
        self.assertEqual(ret.status_int, 200)
        self.app.reset()
        ret2, player2 = self.joinPlayer('arthur', 'test-game-1', 'carlos', 'blue')
        self.assertEqual(ret2.status_int, 200)  
        self.assertNotEqual(ret2.json['uuid'], '')
        self.assertFalse(ret2.json['is_gm'])
        self.assertEqual(ret2.json['error'], '')
        self.assertEqual(ret2.json['playername'], 'carlos')
        self.assertEqual(ret2.json['playercolor'], 'blue')

        # GM can login 
        self.app.set_cookie('session', gm_sid)
        ret3, player3 = self.joinPlayer('arthur', 'test-game-1', 'GM', 'white')
        self.assertEqual(ret3.status_int, 200)  
        self.assertNotEqual(ret3.json['uuid'], '')
        self.assertTrue(ret3.json['is_gm'])
        self.assertEqual(ret3.json['error'], '')
        self.assertEqual(ret3.json['playername'], 'GM')
        self.assertEqual(ret3.json['playercolor'], 'white')

        # register (and login) as another GM
        ret = self.app.post('/vtt/join', {'gmname': 'sneaky'}, xhr=True)
        self.assertEqual(ret.status_int, 200)
        other_sid = self.app.cookies['session']
        self.assertNotEqual(gm_sid, other_sid)
        
        # that other GM is not detected as this game's host GM
        self.app.set_cookie('session', other_sid)
        ret4, player4 = self.joinPlayer('arthur', 'test-game-1', 'fake GM', 'yellow')
        self.assertEqual(ret4.status_int, 200)
        self.assertFalse(ret4.json['is_gm'])   

    def test_websocket(self):
        # @NOTE establishing a websocket is not tested atm
        # instead the method dispatching is tested
        
        # register arthur
        ret = self.app.post('/vtt/join', {'gmname': 'arthur'}, xhr=True)
        self.assertEqual(ret.status_int, 200)
        
        # create a game
        img_small = makeImage(512, 512)
        ret = self.app.post('/vtt/import-game/test-game-1',
            upload_files=[('file', 'test.png', img_small)], xhr=True)
        self.assertEqual(ret.status_int, 200)
        gm_sid = self.app.cookies['session']
        self.app.reset()
        
        # First, the handles are monkey patched to add to a list instead
        log = list()
        gm_cache   = self.engine.cache.getFromUrl('arthur')
        game_cache = gm_cache.getFromUrl('test-game-1')
        game_cache.onPing   = lambda p, d: log.append(('onPing', p, d))
        game_cache.onRoll   = lambda p, d: log.append(('onRoll', p, d))
        game_cache.onSelect = lambda p, d: log.append(('onSelect', p, d))
        game_cache.onRange  = lambda p, d: log.append(('onRange', p, d))
        game_cache.onOrder  = lambda p, d: log.append(('onOrder', p, d))
        game_cache.onUpdateToken   = lambda p, d: log.append(('onUpdateToken', p, d))
        game_cache.onCreateToken   = lambda p, d: log.append(('onCreateToken', p, d))
        game_cache.onCloneToken    = lambda p, d: log.append(('onCloneToken', p, d))
        game_cache.onDeleteToken   = lambda p, d: log.append(('onDeleteToken', p, d))
        game_cache.onBeacon        = lambda p, d: log.append(('onBeacon', p, d))
        game_cache.onMusic         = lambda p, d: log.append(('onMusic', p, d))
        game_cache.onCreateScene   = lambda p, d: log.append(('onCreateScene', p, d))
        game_cache.onActivateScene = lambda p, d: log.append(('onActivateScene', p, d))
        game_cache.onCloneScene    = lambda p, d: log.append(('onCloneScene', p, d))
        game_cache.onDeleteScene   = lambda p, d: log.append(('onDeleteScene', p, d))

        # let player trigger actions
        ret, player_cache = self.joinPlayer('arthur', 'test-game-1', 'merlin', '#FF00FF')
        s = player_cache.socket
        s.block = False
        opids = ['PING', 'ROLL', 'SELECT', 'RANGE', 'ORDER', 'UPDATE', 'CREATE', 'CLONE', 'DELETE', 'BEACON', 'MUSIC', 'GM-CREATE', 'GM-ACTIVATE', 'GM-CLONE', 'GM-DELETE']
        for opid in opids:
            s.push_receive({'OPID': opid, 'data': opid.lower()})
        player_cache.greenlet.join()
        
        # expect actions
        self.assertEqual(len(log), 15)
        self.assertEqual(log[ 0][0], 'onPing')
        self.assertEqual(log[ 1][0], 'onRoll')
        self.assertEqual(log[ 2][0], 'onSelect')
        self.assertEqual(log[ 3][0], 'onRange')
        self.assertEqual(log[ 4][0], 'onOrder')
        self.assertEqual(log[ 5][0], 'onUpdateToken')
        self.assertEqual(log[ 6][0], 'onCreateToken')
        self.assertEqual(log[ 7][0], 'onCloneToken')
        self.assertEqual(log[ 8][0], 'onDeleteToken')
        self.assertEqual(log[ 9][0], 'onBeacon')
        self.assertEqual(log[10][0], 'onMusic')
        self.assertEqual(log[11][0], 'onCreateScene')
        self.assertEqual(log[12][0], 'onActivateScene')
        self.assertEqual(log[13][0], 'onCloneScene')
        self.assertEqual(log[14][0], 'onDeleteScene')
        for i, opid in enumerate(opids):
            self.assertEqual(log[i][1], player_cache)
            self.assertEqual(log[i][2], {'OPID': opid, 'data': opid.lower()})
        
        # cannot trigger unknown operation
        log.clear()
        ret, player_cache = self.joinPlayer('arthur', 'test-game-1', 'merlin', '#FF00FF')
        s = player_cache.socket
        s.block = False
        s.push_receive({'OPID': 'fantasy', 'data': None})
        # expect exception is NOT killing the greenlet (= closing player session)
        self.assertEqual(len(log), 0)

        # cannot trigger operation with too few arguments 
        log.clear()
        game_cache.onRoll = lambda p, d: log.append(('onRoll', p, d['sides']))
        ret, player_cache = self.joinPlayer('arthur', 'test-game-1', 'merlin', '#FF00FF')
        s = player_cache.socket
        s.block = False
        s.push_receive({'OPID': 'ROLL'}) # not providing number of sides etc.
        # expect exception is NOT killing the greenlet (= closing player session)
        self.assertEqual(len(log), 0)

    def test_upload(self):
        # create some images
        img_small  = makeImage(512, 512)   # as token
        img_small2 = makeImage(256, 256)
        img_small3 = makeImage(633, 250)
        img_small4 = makeImage(233, 240)
        img_large  = makeImage(1500, 1500) # as background
        img_huge   = makeImage(2000, 2000) # too large
        mib = 2**20
        self.assertLess(len(img_small), mib)       
        self.assertLess(len(img_large), (self.engine.file_limit['background'] + 1) * mib)
        self.assertGreater(len(img_large), (self.engine.file_limit['background'] // 2) * mib)  
        self.assertGreater(len(img_huge), self.engine.file_limit['background'] * mib)
        
        id_from_url = lambda s: int(s.split('/')[-1].split('.png')[0])
        
        # register arthur
        ret = self.app.post('/vtt/join', {'gmname': 'arthur'}, xhr=True)
        self.assertEqual(ret.status_int, 200)
        
        # create a game
        img_small = makeImage(512, 512)
        ret = self.app.post('/vtt/import-game/test-game-1',
            upload_files=[('file', 'test.png', img_small)], xhr=True)
        self.assertEqual(ret.status_int, 200)
        gm_sid = self.app.cookies['session']
        self.app.reset()
        
        # players can upload tokens to an existing game
        ret = self.app.post('/arthur/test-game-1/upload',
            upload_files=[
                ('file[]', 'test.png', img_small2),
                ('file[]', 'another.png', img_small3)
            ], xhr=True)
        self.assertEqual(ret.status_int, 200)
        # @NOTE: non-json response but with json-dumped data
        # I need to find a way to answer with a json-response to an
        # upload post (from jQuery)
        data = json.loads(ret.body)
        self.assertEqual(len(data['urls']), 2)
        self.assertFalse(data['music'])
        self.assertEqual(id_from_url(data['urls'][0]), 1) # since 0 is background
        self.assertEqual(id_from_url(data['urls'][1]), 2)

        # re-uploading image will return existing URLs instead of new ones
        ret = self.app.post('/arthur/test-game-1/upload',
            upload_files=[
                ('file[]', 'test.png', img_small2),
                ('file[]', 'another.bmp', img_small3),
                ('file[]', 'foo.png', img_small3),
                ('file[]', 'random.tiff', img_small3),
                ('file[]', 'something.gif', img_small2),
                ('file[]', 'weird.jpg', img_small3)
            ], xhr=True)
        self.assertEqual(ret.status_int, 200)
        data = json.loads(ret.body)
        self.assertEqual(len(data['urls']), 6)
        self.assertFalse(data['music'])
        self.assertEqual(id_from_url(data['urls'][0]), 1)
        self.assertEqual(id_from_url(data['urls'][1]), 2)
        self.assertEqual(id_from_url(data['urls'][2]), 2)
        self.assertEqual(id_from_url(data['urls'][3]), 2)
        self.assertEqual(id_from_url(data['urls'][4]), 1)
        self.assertEqual(id_from_url(data['urls'][5]), 2)

        # cannot upload another background image (other uploads are ignored during this request)
        images = os.listdir(self.engine.paths.getGamePath('arthur', 'test-game-1'))
        self.assertEqual(len(images), 4) # 3 + md5-file
        ret = self.app.post('/arthur/test-game-1/upload',
            upload_files=[
                ('file[]', 'another.jpg', img_small4),
                ('file[]', 'test.png', img_large),
                ('file[]', 'another.jpg', img_small4)
            ], xhr=True, expect_errors=True)
        self.assertEqual(ret.status_int, 403)
        # expect no new images in directory
        images = os.listdir(self.engine.paths.getGamePath('arthur', 'test-game-1'))
        self.assertEqual(len(images), 4) # 3 + md5-file
        self.assertIn('0.png', images)
        self.assertIn('1.png', images)
        self.assertIn('2.png', images)
        self.assertNotIn('3.png', images)

        # can upload background and tokens in new scene
        gm_cache   = self.engine.cache.getFromUrl('arthur')
        game_cache = gm_cache.getFromUrl('test-game-1')
        gm_player  = game_cache.insert('GM Arthur', 'red', True)
        game_cache.onCreateScene(gm_player, {})
        ret = self.app.post('/arthur/test-game-1/upload',
            upload_files=[
                ('file[]', 'test.png', img_large),
                ('file[]', 'another.jpg', img_small2),
                ('file[]', 'another.jpg', img_small3)
            ], xhr=True, expect_errors=True)
        self.assertEqual(ret.status_int, 200)
        data = json.loads(ret.body)
        self.assertEqual(len(data['urls']), 3)
        self.assertFalse(data['music'])
        self.assertEqual(id_from_url(data['urls'][0]), 3)
        self.assertEqual(id_from_url(data['urls'][1]), 1)
        self.assertEqual(id_from_url(data['urls'][2]), 2)
        
        # cannot upload huge image as background
        gm_cache   = self.engine.cache.getFromUrl('arthur')
        game_cache = gm_cache.getFromUrl('test-game-1')
        gm_player  = game_cache.insert('GM Arthur', 'red', True)
        game_cache.onCreateScene(gm_player, {})
        ret = self.app.post('/arthur/test-game-1/upload',
            upload_files=[
                ('file[]', 'test.png', img_huge)
            ], xhr=True, expect_errors=True)
        self.assertEqual(ret.status_int, 403)

        # cannot upload image to unknown game
        ret = self.app.post('/arthur/test-game-1456/upload',
            upload_files=[
                ('file[]', 'test.png', img_small2),
                ('file[]', 'another.png', img_small3)
            ], xhr=True, expect_errors=True)
        self.assertEqual(ret.status_int, 404)
        
        # cannot upload image to unknown GM
        ret = self.app.post('/bob/test-game-1/upload',
            upload_files=[
                ('file[]', 'test.png', img_small2),
                ('file[]', 'another.png', img_small3)
            ], xhr=True, expect_errors=True)
        self.assertEqual(ret.status_int, 404)

        # cannot upload unsupported mime type 
        ret = self.app.post('/arthur/test-game-1/upload',
            upload_files=[
                ('file[]', 'test.png', img_small2),
                ('file[]', 'foo.exe', b''),
                ('file[]', 'another.png', img_small3)
            ], xhr=True, expect_errors=True)
        self.assertEqual(ret.status_int, 403)
        
        root = self.engine.paths.getGamePath('arthur', 'test-game-1')
        count_mp3s = lambda: len([f for f in os.listdir(root) if f.endswith('.mp3')])
        
        # can upload music
        self.assertEqual(count_mp3s(), 0)
        ret = self.app.post('/arthur/test-game-1/upload',
            upload_files=[
                ('file[]', 'sample.mp3', b'')
            ], xhr=True)
        self.assertEqual(ret.status_int, 200) 
        data = json.loads(ret.body)
        self.assertEqual(len(data['urls']), 0)
        self.assertEqual(data['music'], [0])
        self.assertEqual(count_mp3s(), 1)

        # can upload multiple tracks
        ret = self.app.post('/arthur/test-game-1/upload',
            upload_files=[
                ('file[]', 'sample.mp3', b''),
                ('file[]', 'foo.mp3', b''),
                ('file[]', 'three.mp3', b'')
            ], xhr=True)
        self.assertEqual(ret.status_int, 200) 
        data = json.loads(ret.body)
        self.assertEqual(len(data['urls']), 0)
        self.assertEqual(data['music'], [1, 2, 3])
        self.assertEqual(count_mp3s(), 4)
        
        # can upload music and images
        ret = self.app.post('/arthur/test-game-1/upload',
            upload_files=[                
                ('file[]', 'test.png', img_small2),
                ('file[]', 'sample.mp3', b''),
                ('file[]', 'another.png', img_small3)
            ], xhr=True)
        self.assertEqual(ret.status_int, 200) 
        data = json.loads(ret.body)
        self.assertEqual(len(data['urls']), 2) 
        self.assertEqual(id_from_url(data['urls'][0]), 1)
        self.assertEqual(id_from_url(data['urls'][1]), 2)
        self.assertEqual(data['music'], [4])
        self.assertEqual(count_mp3s(), 5)

        # cannot upload too much music (referring music slots)
        self.assertEqual(self.engine.file_limit['num_music'], 5)
        ret = self.app.post('/arthur/test-game-1/upload',
            upload_files=[
                ('file[]', 'sample.mp3', b''),
                ('file[]', 'foo.mp3', b'')
            ], xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(count_mp3s(), 5)

    def test_music(self):
        id_from_url = lambda s: int(s.split('/')[-1].split('.png')[0])
        
        # register arthur
        ret = self.app.post('/vtt/join', {'gmname': 'arthur'}, xhr=True)
        self.assertEqual(ret.status_int, 200)
        
        # create a game
        img_small = makeImage(512, 512)
        ret = self.app.post('/vtt/import-game/test-game-1',
            upload_files=[('file', 'test.png', img_small)], xhr=True)
        self.assertEqual(ret.status_int, 200)
        gm_sid = self.app.cookies['session']
        self.app.reset()
        
        # upload music     
        ret = self.app.post('/arthur/test-game-1/upload',
            upload_files=[
                ('file[]', 'sample.mp3', b''),
                ('file[]', 'foo.mp3', b''),
                ('file[]', 'three.mp3', b''),
                ('file[]', 'four.mp3', b'')
            ], xhr=True)
        self.assertEqual(ret.status_int, 200) 
        data = json.loads(ret.body)
        self.assertEqual(len(data['urls']), 0)
        self.assertEqual(data['music'], [0, 1, 2, 3])

        # can query existing slots
        for slot_id in data['music']:
            ret = self.app.get('/music/arthur/test-game-1/{0}.mp3?update=0815'.format(slot_id))
            self.assertEqual(ret.status_int, 200)

        # cannot query invalid slot
        ret = self.app.get('/music/arthur/test-game-1/14.mp3?update=0815', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_upload_background(self):
        # create some images
        img_large  = makeImage(1500, 1500) # as background
        img_huge   = makeImage(2000, 2000) # too large
        mib = 2**20
        self.assertGreater(len(img_large), (self.engine.file_limit['background'] // 2) * mib)  
        self.assertGreater(len(img_huge), self.engine.file_limit['background'] * mib)
        
        # register arthur
        ret = self.app.post('/vtt/join', {'gmname': 'arthur'}, xhr=True)
        self.assertEqual(ret.status_int, 200)
        
        # create a game
        img_small = makeImage(512, 512)
        ret = self.app.post('/vtt/import-game/test-game-1',
            upload_files=[('file', 'test.png', img_small)], xhr=True)
        self.assertEqual(ret.status_int, 200)
        gm_sid = self.app.cookies['session']
        self.app.reset()
        
        # players can upload new background to an existing game
        ret = self.app.post('/vtt/upload-background/arthur/test-game-1',
            upload_files=[
                ('file[]', 'back.png', img_large)
            ], xhr=True, expect_errors=True)
        self.assertEqual(ret.status_int, 404)

        # login as GM
        self.app.set_cookie('session', gm_sid)

        id_from_url = lambda s: int(s.split('/')[-1].split('.png')[0])
        
        # gm can upload background to an existing game
        ret = self.app.post('/vtt/upload-background/arthur/test-game-1',
            upload_files=[
                ('file[]', 'back.png', img_large)
            ], xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(id_from_url(str(ret.body)), 1)
        
        # gm cannot upload multiple files as background
        ret = self.app.post('/vtt/upload-background/arthur/test-game-1',
            upload_files=[
                ('file[]', 'back.png', img_large),
                ('file[]', 'back2.png', img_large)
            ], xhr=True, expect_errors=True)
        self.assertEqual(ret.status_int, 403)
        
        # gm cannot upload too large file as background
        ret = self.app.post('/vtt/upload-background/arthur/test-game-1',
            upload_files=[
                ('file[]', 'back.png', img_huge)
            ], xhr=True, expect_errors=True)
        self.assertEqual(ret.status_int, 403)
    
