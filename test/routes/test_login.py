"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

from test.common import EngineBaseTest, make_image
from vtt import routes


class LoginRoutesTest(EngineBaseTest):

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

    def test_expect_redirect_if_session_is_invalid(self):
        self.app.set_cookie('session', 'randomstuffthatisnotasessionid')
        ret = self.app.get('/')
        self.assertEqual(ret.status_int, 302)
        # FIXME: setting cookie is ignored on redirect
        # self.assertEqual(self.app.cookies['session'], '""')

    def test_can_access_login_screen_for_existing_game(self):
        ret = self.app.get('/game/arthur/test-game-1')
        self.assertEqual(ret.status_int, 200)
        # expect GM dropdown NOT to be loaded
        self.assertNotIn('onClick="addScene();"', ret.unicode_normal_body)

    def test_can_access_game_login_as_GM(self):
        self.app.set_cookie('session', self.sid)
        ret = self.app.get('/game/arthur/test-game-1')
        self.assertEqual(ret.status_int, 200)
        # expect GM dropdown to be loaded
        self.assertIn('onClick="addScene();"', ret.unicode_normal_body)

    def test_cannot_access_unknown_games_login(self):
        ret = self.app.get('/game/arthur/test-game-2', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_cannot_access_unknown_GMs_game_login(self):
        ret = self.app.get('/game/bob/test-game-2', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_players_can_login(self):
        ret1, player1 = self.join_player('arthur', 'test-game-1', 'bob', 'red')
        self.assertEqual(ret1.status_int, 200)
        self.assertNotEqual(ret1.json['uuid'], '')
        self.assertEqual(ret1.json['error'], '')
        self.assertFalse(ret1.json['is_gm'])
        self.assertEqual(ret1.json['playername'], 'bob')
        self.assertEqual(ret1.json['playercolor'], 'red')

        ret2, player2 = self.join_player('arthur', 'test-game-1', 'carlos', 'blue')
        self.assertEqual(ret2.status_int, 200)
        self.assertNotEqual(ret2.json['uuid'], '')
        self.assertFalse(ret2.json['is_gm'])
        self.assertEqual(ret2.json['error'], '')
        self.assertEqual(ret2.json['playername'], 'carlos')
        self.assertEqual(ret2.json['playercolor'], 'blue')

    def test_cannot_login_if_name_already_in_use(self):
        ret2, player2 = self.join_player('arthur', 'test-game-1', 'carlos', 'blue')
        self.assertEqual(ret2.status_int, 200)
        self.assertNotEqual(ret2.json['uuid'], '')
        self.assertFalse(ret2.json['is_gm'])
        self.assertEqual(ret2.json['error'], '')
        self.assertEqual(ret2.json['playername'], 'carlos')
        self.assertEqual(ret2.json['playercolor'], 'blue')

        ret = self.app.post('/game/arthur/test-game-1/login', {'playername': 'carlos', 'playercolor': 'blue'})
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.json['uuid'], '')
        self.assertFalse(ret.json['is_gm'])
        self.assertEqual(ret.json['error'], 'ALREADY IN USE')
        self.assertEqual(ret.json['playername'], '')
        self.assertEqual(ret.json['playercolor'], '')

    def test_cannot_login_with_empty_name(self):
        ret = self.app.post('/game/arthur/test-game-1/login', {'playername': '', 'playercolor': 'blue'})
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.json['uuid'], '')
        self.assertFalse(ret.json['is_gm'])
        self.assertEqual(ret.json['error'], 'PLEASE ENTER A NAME')
        self.assertEqual(ret.json['playername'], '')
        self.assertEqual(ret.json['playercolor'], '')

    def test_cannot_login_to_unknown_game(self):
        ret = self.app.post('/game/arthur/test-game-2/login', {'playername': 'dagmar', 'playercolor': 'black'})
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.json['uuid'], '')
        self.assertFalse(ret.json['is_gm'])
        self.assertEqual(ret.json['error'], 'GAME NOT FOUND')
        self.assertEqual(ret.json['playername'], '')
        self.assertEqual(ret.json['playercolor'], '')

    def test_cannot_login_to_unknown_GMs_game(self):
        ret = self.app.post('/game/horatio/test-game-1/login', {'playername': 'dagmar', 'playercolor': 'black'})
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.json['uuid'], '')
        self.assertFalse(ret.json['is_gm'])
        self.assertEqual(ret.json['error'], 'GAME NOT FOUND')
        self.assertEqual(ret.json['playername'], '')
        self.assertEqual(ret.json['playercolor'], '')

    def test_can_relogin_after_being_kicked(self):
        # login player2
        ret2, player2 = self.join_player('arthur', 'test-game-1', 'carlos', 'blue')
        self.assertEqual(ret2.status_int, 200)
        self.assertNotEqual(ret2.json['uuid'], '')
        self.assertFalse(ret2.json['is_gm'])
        self.assertEqual(ret2.json['error'], '')
        self.assertEqual(ret2.json['playername'], 'carlos')
        self.assertEqual(ret2.json['playercolor'], 'blue')

        # kick as GM
        self.app.set_cookie('session', self.sid)
        ret = self.app.post('/vtt/kick-player/test-game-1/{0}'.format(player2.uuid))
        self.assertEqual(ret.status_int, 200)
        self.app.reset()

        # player2 re-login
        ret2, player2 = self.join_player('arthur', 'test-game-1', 'carlos', 'blue')
        self.assertEqual(ret2.status_int, 200)
        self.assertNotEqual(ret2.json['uuid'], '')
        self.assertFalse(ret2.json['is_gm'])
        self.assertEqual(ret2.json['error'], '')
        self.assertEqual(ret2.json['playername'], 'carlos')
        self.assertEqual(ret2.json['playercolor'], 'blue')

    def test_GM_can_login_to_his_game(self):
        self.app.set_cookie('session', self.sid)

        ret3, player3 = self.join_player('arthur', 'test-game-1', 'GM', 'white')
        self.assertEqual(ret3.status_int, 200)
        self.assertNotEqual(ret3.json['uuid'], '')
        self.assertTrue(ret3.json['is_gm'])
        self.assertEqual(ret3.json['error'], '')
        self.assertEqual(ret3.json['playername'], 'GM')
        self.assertEqual(ret3.json['playercolor'], 'white')

    def test_GM_can_login_to_another_GMs_game(self):
        self.app.set_cookie('session', self.sid)

        ret = self.app.post('/vtt/join', {'gmname': 'sneaky'}, xhr=True)
        self.assertEqual(ret.status_int, 200)
        other_sid = self.app.cookies['session']
        self.assertNotEqual(self.sid, other_sid)

        # that other GM is not detected as this game's host GM
        self.app.set_cookie('session', other_sid)
        ret4, player4 = self.join_player('arthur', 'test-game-1', 'fake GM', 'yellow')
        self.assertEqual(ret4.status_int, 200)
        self.assertFalse(ret4.json['is_gm'])
