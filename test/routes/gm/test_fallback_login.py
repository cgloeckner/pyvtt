"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

from test.common import EngineBaseTest, make_image
from vtt import routes


class GmFallbackLoginRoutesTest(EngineBaseTest):

    def setUp(self):
        super().setUp()
        routes.register_gm(self.engine)
        routes.register_player(self.engine)
        routes.register_resources(self.engine)
        # @NOTE: custom error pages are not routed here

    def test_post_vtt_join(self):
        # @NOTE: this route is working because the engine was loaded without auth-support, hence GMs can create an
        # account directly (dev fallback)

        # can create a GM account
        args = {
            'gmname': 'arthur'
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
            'gmname': 'arthurhasaverylongnamethatiscutafter20chars'
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

    def test_vtt_post_join_root(self):
        # register arthur
        ret = self.app.post('/vtt/join', {'gmname': 'arthur'}, xhr=True)
        self.assertEqual(ret.status_int, 200)

        # create a game
        img_small = make_image(512, 512)
        self.app.post('/vtt/import-game/test-exportgame-1',
                      upload_files=[('file', 'test.png', img_small)], xhr=True)
        # expect landing page
        ret = self.app.get('/')
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'text/html')
        self.assertNotEqual(ret.location, 'http://localhost:80/vtt/join')
