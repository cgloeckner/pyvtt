"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2024 Christian Glöckner
License: MIT (see LICENSE for details)
"""

from test.common import EngineBaseTest, make_image
from vtt import routes, orm


class GmLoginRoutesTest(EngineBaseTest):

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

        # create a game
        img_small = make_image(512, 512)
        ret = self.app.post('/vtt/import-game/test-game-1',
                            upload_files=[('file', 'test.png', img_small)], xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.sid = self.app.cookies['session']
        self.app.reset()

    def test_root_redirects_to_login(self):
        ret = self.app.get('/')
        self.assertEqual(ret.status_int, 302)
        self.assertEqual(ret.location, 'http://localhost:80/vtt/join')
        ret = ret.follow()
        self.assertEqual(ret.status_int, 200)

    def test_expect_games_menu_if_logged_in(self):
        ret = self.app.post('/vtt/join', {'gmname': 'bob'}, xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertIn('session', self.app.cookies)
        ret = self.app.get('/')
        self.assertEqual(ret.status_int, 200)

    def test_cannot_show_games_if_gm_is_not_known(self):
        ret = self.app.post('/vtt/join', {'gmname': 'bob'}, xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertIn('session', self.app.cookies)

        with orm.db_session:
            gm = self.engine.main_db.GM.select(lambda g: g.url == 'bob').first()
            self.engine.cache.remove(gm)

        ret = self.app.get('/', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_expect_redirect_if_session_is_invalid(self):
        self.app.set_cookie('session', 'randomstuffthatisnotasessionid')
        ret = self.app.get('/')
        self.assertEqual(ret.status_int, 302)
        # FIXME: setting cookie is ignored on redirect
        # self.assertEqual(self.app.cookies['session'], '""')

    def test_can_logout(self):
        ret = self.app.post('/vtt/join', {'gmname': 'bob'}, xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertIn('session', self.app.cookies)

        ret = self.app.get('/vtt/logout')
        self.assertEqual(ret.status_int, 302)
        self.assertEqual(self.app.cookies['session'], '""')

    def test_can_even_attempt_logout_if_not_logged_in(self):
        ret = self.app.get('/vtt/logout')
        self.assertEqual(ret.status_int, 302)
        self.assertEqual(self.app.cookies['session'], '""')
