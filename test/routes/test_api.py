"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import requests
import gevent

from test.common import EngineBaseTest, make_image
from vtt import routes


class ApiRoutesTest(EngineBaseTest):

    def setUp(self):
        super().setUp()
        routes.register_gm(self.engine)
        routes.register_player(self.engine)
        routes.register_resources(self.engine)
        routes.register_api(self.engine)
        # @NOTE: custom error pages are not routed here

    def test_api_get_queries(self):
        ret = self.app.get('/vtt/api/users', expect_errors=True)
        self.assertEqual(ret.status_int, 200)

        ret = self.app.get('/vtt/api/logins', expect_errors=True)
        self.assertEqual(ret.status_int, 200)

        ret = self.app.get('/vtt/api/auth', expect_errors=True)
        self.assertEqual(ret.status_int, 200)

    def test_cannot_query_games_and_assets_as_default_user(self):
        # register arthur
        ret = self.app.post('/vtt/join', {'gmname': 'arthur'}, xhr=True)
        self.assertEqual(ret.status_int, 200)

        # create a game
        img_small = make_image(512, 512)
        ret = self.app.post('/vtt/import-game/test-game-1',
                            upload_files=[('file', 'test.png', img_small)], xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.app.reset()

        ret = self.app.get('/vtt/api/games-list/arthur', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

        ret = self.app.get('/vtt/api/assets-list/arthur/test-game-1', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_can_query_games_and_assets_as_gm(self):
        # register arthur
        ret = self.app.post('/vtt/join', {'gmname': 'arthur'}, xhr=True)
        self.assertEqual(ret.status_int, 200)

        # create a game
        img_small = make_image(512, 512)
        ret = self.app.post('/vtt/import-game/test-game-1', upload_files=[('file', 'test.png', img_small)], xhr=True)
        self.assertEqual(ret.status_int, 200)
        gm_sid = self.app.cookies['session']
        self.app.reset()

        # login as arthur
        self.app.set_cookie('session', gm_sid)

        ret = self.app.get('/vtt/api/games-list/arthur', expect_errors=True)
        self.assertEqual(ret.status_int, 200)

        ret = self.app.get('/vtt/api/assets-list/arthur/test-game-1', expect_errors=True)
        self.assertEqual(ret.status_int, 200)

    def test_can_post_maintenance_timestamp(self) -> None:
        ret = self.app.post('/vtt/api/maintenance/1234')
        self.assertEqual(ret.status_int, 200)

        self.assertEqual(self.engine.maintenance.load(), 1234)
