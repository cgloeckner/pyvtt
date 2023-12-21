"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

from test.common import EngineBaseTest, make_image
from vtt import routes


class GmExportRoutesTest(EngineBaseTest):

    def setUp(self):
        super().setUp()
        routes.register_gm(self.engine)
        routes.register_player(self.engine)
        routes.register_resources(self.engine)
        routes.register_api(self.engine)
        # @NOTE: custom error pages are not routed here

        # register arthur
        ret = self.app.post('/vtt/join', {'gmname': 'arthur'}, xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.sid = self.app.cookies['session']

        # create a game
        img_small = make_image(512, 512)
        ret = self.app.post('/vtt/import-game/test-exportgame-1', upload_files=[('file', 'test.png', img_small)],
                            xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'application/json')
        self.assertTrue(ret.json['url_ok'])
        self.assertTrue(ret.json['file_ok'])
        self.assertEqual(ret.json['error'], '')
        self.assertEqual(ret.json['url'], 'game/arthur/test-exportgame-1')

        # register bob
        ret = self.app.post('/vtt/join', {'gmname': 'bob'}, xhr=True)
        self.assertEqual(ret.status_int, 200)

        # create a game
        img_small = make_image(512, 512)
        ret = self.app.post('/vtt/import-game/this-one-is-bob', upload_files=[('file', 'test.png', img_small)],
                            xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'application/json')
        self.assertTrue(ret.json['url_ok'])
        self.assertTrue(ret.json['file_ok'])
        self.assertEqual(ret.json['error'], '')
        self.assertEqual(ret.json['url'], 'game/bob/this-one-is-bob')

        # reset app to clear cookies
        self.app.reset()

    def test_cannot_export_game_without_GM_session(self):
        ret = self.app.get('/vtt/export-game/test-exportgame-1', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_cannot_export_game_using_invalid_session(self):
        self.app.set_cookie('session', 'something-that-shall-fake-a-session')

        ret = self.app.get('/vtt/export-game/test-exportgame-1', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_can_export_your_game(self):
        self.app.set_cookie('session', self.sid)

        ret = self.app.get('/vtt/export-game/test-exportgame-1')
        self.assertEqual(ret.status_int, 200)

    def test_cannot_export_another_gms_game(self):
        self.app.set_cookie('session', self.sid)

        ret = self.app.get('/vtt/export-game/this-one-is-bob', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_cannot_export_non_existing_game(self):
        ret = self.app.get('/vtt/export-game/test-anything-else', expect_errors=True)
        self.assertEqual(ret.status_int, 404)
