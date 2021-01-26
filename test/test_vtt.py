#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import tempfile, json, os, zipfile

from PIL import Image

import vtt

from test.utils import EngineBaseTest


class VttTest(EngineBaseTest):

    def setUp(self):
        super().setUp()
        vtt.setup_gm_routes(self.engine)
        vtt.setup_player_routes(self.engine)
        # @NOTE: custom errorpages are not routed here
    
    def test_get_root(self):
        # expect redirect to login
        ret = self.app.get('/')
        self.assertEqual(ret.status_int, 302) # redirect
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
        def img2bytes(w, h):
            pil_img = Image.new(mode='RGB', size=(w, h))
            with tempfile.NamedTemporaryFile('wb') as wh:
                pil_img.save(wh.name, 'BMP')
                with open(wh.name, 'rb') as rh:
                    return rh.read()
        img_small = img2bytes(512, 512)
        img_large = img2bytes(1500, 1500)
        img_huge  = img2bytes(2000, 2000)
        mib = 2**20
        self.assertLess(len(img_small), mib)       
        self.assertLess(len(img_large), 11 * mib)
        self.assertGreater(len(img_large), 5 * mib)  
        self.assertGreater(len(img_huge), 10 * mib)

        # create some zips
        empty_game = json.dumps({
            'tokens': [],
            'scenes': [{'tokens': [], 'backing': None}]
        })
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
        
        zip_normal = makeZip('zip2', empty_game, 4)
        zip_huge   = makeZip('zip2', empty_game, 8)
        self.assertLess(len(zip_normal), 15 * mib)
        self.assertGreater(len(zip_huge), 15 * mib)
        
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
            upload_files=[('file', 'test.png', img_small)], xhr=True)
        self.assertEqual(ret.status_int, 302) # redirect
        self.assertEqual(ret.location, 'http://localhost:80/vtt/join')
        ret = ret.follow()
        self.assertEqual(ret.status_int, 200) # login

        # cannot import zip without GM session
        ret = self.app.post('/vtt/import-game/',
            upload_files=[('file', 'test.zip', img_small)], xhr=True)
        self.assertEqual(ret.status_int, 302) # redirect
        self.assertEqual(ret.location, 'http://localhost:80/vtt/join')
        ret = ret.follow()   
        self.assertEqual(ret.status_int, 200) # login

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
        
        # cannot import image with invalid url
        ret = self.app.post('/vtt/import-game/test url-2',
            upload_files=[('file', 'test.png', img_small)], xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'application/json')   
        self.assertEqual(ret.json['error'], 'NO SPECIAL CHARS OR SPACES')
        self.assertEqual(ret.json['url'], '')
        self.assertFalse(ret.json['url_ok'])
        
        # cannot import multiple files at once
        for url in ['', 'test-url-3']:
            ret = self.app.post('/vtt/import-game/{0}'.format(url),
                upload_files=[
                    ('file', 'test.png', img_small),
                    ('file', 'test.png', img_small)
                ], xhr=True)
            self.assertEqual(ret.status_int, 200)
            self.assertEqual(ret.content_type, 'application/json') 
            self.assertTrue(ret.json['url_ok'])
            self.assertFalse(ret.json['file_ok'])
            self.assertEqual(ret.json['error'], 'ONE FILE AT ONCE')
        
        # can upload large background
        for url in ['', 'test-url-4']:
            ret = self.app.post('/vtt/import-game/{0}'.format(url),
                upload_files=[('file', 'test.png', img_large)], xhr=True)
            self.assertEqual(ret.status_int, 200)
            self.assertEqual(ret.content_type, 'application/json')
            self.assertTrue(ret.json['url_ok'])
            self.assertTrue(ret.json['file_ok'])
            self.assertEqual(ret.json['error'], '')
            if url != '':
                self.assertEqual(ret.json['url'], 'arthur/test-url-4')
            
        # cannot upload too large background
        for url in ['', 'test-url-5']:
            ret = self.app.post('/vtt/import-game/{0}'.format(url),
                upload_files=[('file', 'test.png', img_huge)], xhr=True)
            self.assertEqual(ret.status_int, 200)
            self.assertEqual(ret.content_type, 'application/json')
            self.assertTrue(ret.json['url_ok'])
            self.assertFalse(ret.json['file_ok'])
            self.assertEqual(ret.json['error'], 'TOO LARGE BACKGROUND (MAX 10 MiB)')
            self.assertEqual(ret.json['url'], '')
        
        # cannot upload a fake zip file
        for url in ['', 'test-url-6']:
            ret = self.app.post('/vtt/import-game/{0}'.format(url),
                upload_files=[('file', 'test.zip', fake_file)], xhr=True)
            self.assertEqual(ret.status_int, 200)
            self.assertEqual(ret.content_type, 'application/json')
            self.assertTrue(ret.json['url_ok'])
            self.assertFalse(ret.json['file_ok'])
            self.assertEqual(ret.json['error'], 'CORRUPTED FILE')   
            self.assertEqual(ret.json['url'], '')
        
        # can upload zip file
        for url in ['', 'test-url-7']:
            ret = self.app.post('/vtt/import-game/{0}'.format(url),
                upload_files=[('file', 'test.zip', zip_normal)], xhr=True)
            self.assertEqual(ret.status_int, 200)
            self.assertEqual(ret.content_type, 'application/json')
            self.assertTrue(ret.json['url_ok'])
            self.assertTrue(ret.json['file_ok'])
            self.assertEqual(ret.json['error'], '')
        
        # cannot upload too large zip file
        for url in ['', 'test-url-8']:
            ret = self.app.post('/vtt/import-game/{0}'.format(url),
                upload_files=[('file', 'test.zip', zip_huge)], xhr=True)
            self.assertEqual(ret.status_int, 200)
            self.assertEqual(ret.content_type, 'application/json')
            self.assertTrue(ret.json['url_ok'])
            self.assertFalse(ret.json['file_ok'])
            self.assertEqual(ret.json['error'], 'TOO LARGE GAME (MAX 15 MiB)')
        
        # cannot upload any other file format
        for url in ['', 'test-url-9']:
            ret = self.app.post('/vtt/import-game/{0}'.format(url),
                upload_files=[('file', 'test.txt', text_file)], xhr=True)
            self.assertEqual(ret.status_int, 200)
            self.assertEqual(ret.content_type, 'application/json')
            self.assertTrue(ret.json['url_ok'])
            self.assertFalse(ret.json['file_ok'])
            self.assertEqual(ret.json['error'], 'USE AN IMAGE FILE')
            self.assertEqual(ret.json['url'], '')

        
        
    # @NOTE: next is /vtt/export-game
