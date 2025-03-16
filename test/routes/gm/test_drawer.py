"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import json

import gevent

from test.common import EngineBaseTest, make_image
from vtt import routes, orm


class GmGamesRoutesTest(EngineBaseTest):

    def setUp(self):
        super().setUp()
        routes.register_gm(self.engine)
        routes.register_player(self.engine)
        routes.register_resources(self.engine)
        # @NOTE: custom error pages are not routed here

        # FIXME: move to EngineBaseTest (create_arthur) -> session_id
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

    def test_can_access_GM_login(self):
        ret = self.app.get('/vtt/join')
        self.assertEqual(ret.status_int, 200)

    def test_can_create_fancy_url(self):
        ret = self.app.get('/vtt/fancy-url')
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'text/html')

        # expect 3 words separated with 2 '-'
        fancy_url = ret.unicode_normal_body
        self.assertEqual(len(fancy_url.split('-')), 3)
        for word in fancy_url.split('-'):
            self.assertNotEqual(word, '')
    
    def test_cannot_cleanup_as_a_player(self):
        self.join_player('arthur', 'test-game-1', 'arthur', 'gold')
        self.join_player('arthur', 'test-game-1', 'bob', 'red')
        self.join_player('arthur', 'test-game-1', 'carlos', 'blue')

        gm_cache = self.engine.cache.get_from_url('arthur')
        game_cache = gm_cache.get_from_url('test-game-1')
        self.assertEqual(len(game_cache.players), 3)

        ret = self.app.post('/vtt/clean-up/test-game-1', expect_errors=True)
        self.assertEqual(ret.status_int, 404)
        self.assertEqual(len(game_cache.players), 3)

    def test_GM_cannot_cleanup_unknown_game(self):
        self.app.set_cookie('session', self.sid)

        self.join_player('arthur', 'test-game-1', 'arthur', 'gold')
        self.join_player('arthur', 'test-game-1', 'bob', 'red')
        self.join_player('arthur', 'test-game-1', 'carlos', 'blue')

        gm_cache = self.engine.cache.get_from_url('arthur')
        game_cache = gm_cache.get_from_url('test-game-1')
        self.assertEqual(len(game_cache.players), 3)

        ret = self.app.post('/vtt/clean-up/test-weird', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_cannot_cleanup_as_unknown_gm(self):
        self.app.set_cookie('session', self.sid)

        self.join_player('arthur', 'test-game-1', 'arthur', 'gold')
        self.join_player('arthur', 'test-game-1', 'bob', 'red')
        self.join_player('arthur', 'test-game-1', 'carlos', 'blue')

        with orm.db_session:
            gm = self.engine.main_db.GM.select(lambda g: g.url == 'arthur').first()
            self.engine.cache.remove(gm)

        ret = self.app.post('/vtt/clean-up/test-game-1', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_GM_can_cleanup_his_game(self):
        self.join_player('arthur', 'test-game-1', 'arthur', 'gold')
        self.join_player('arthur', 'test-game-1', 'bob', 'red')
        self.join_player('arthur', 'test-game-1', 'carlos', 'blue')

        gm_cache = self.engine.cache.get_from_url('arthur')
        game_cache = gm_cache.get_from_url('test-game-1')
        self.assertEqual(len(game_cache.players), 3)

        # upload some music
        self.app.post('/game/arthur/test-game-1/upload', upload_files=[('file[]', 'sample.mp3', b'')], xhr=True)

        self.app.set_cookie('session', self.sid)
        ret = self.app.post('/vtt/clean-up/test-game-1')
        self.assertEqual(ret.status_int, 200)
        # FIXME: expect music websockets to contain music refresh action

    def test_players_cannot_kick_a_player(self):
        ret1, player1 = self.join_player('arthur', 'test-game-1', 'arthur', 'gold')
        ret2, player2 = self.join_player('arthur', 'test-game-1', 'bob', 'red')
        ret3, player3 = self.join_player('arthur', 'test-game-1', 'carlos', 'blue')
        self.join_player('arthur', 'test-game-1', 'blocker', 'green')

        gm_cache = self.engine.cache.get_from_url('arthur')
        game_cache = gm_cache.get_from_url('test-game-1')
        self.assertEqual(len(game_cache.players), 4)

        for p in [player1, player2, player3]:
            ret = self.app.post('/vtt/kick-player/test-game-1/{0}'.format(p.uuid), expect_errors=True)
            self.assertEqual(ret.status_int, 404)
            self.assertEqual(len(game_cache.players), 4)

    def test_players_cannot_kick_a_player_from_unknown_game(self):
        ret1, player1 = self.join_player('arthur', 'test-game-1', 'arthur', 'gold')
        ret2, player2 = self.join_player('arthur', 'test-game-1', 'bob', 'red')
        ret3, player3 = self.join_player('arthur', 'test-game-1', 'carlos', 'blue')
        self.join_player('arthur', 'test-game-1', 'blocker', 'green')

        gm_cache = self.engine.cache.get_from_url('arthur')
        game_cache = gm_cache.get_from_url('test-game-1')
        self.assertEqual(len(game_cache.players), 4)

        for p in [player1, player2, player3]:
            ret = self.app.post('/vtt/kick-player/test-weird-1/{0}'.format(p.uuid), expect_errors=True)
            self.assertEqual(ret.status_int, 404)
            self.assertEqual(len(game_cache.players), 4)

    def test_cannot_kick_as_unknown_gm(self):
        self.join_player('arthur', 'test-game-1', 'arthur', 'gold')
        ret2, player2 = self.join_player('arthur', 'test-game-1', 'bob', 'red')
        self.join_player('arthur', 'test-game-1', 'carlos', 'blue')
        self.join_player('arthur', 'test-game-1', 'blocker', 'green')

        with orm.db_session:
            gm = self.engine.main_db.GM.select(lambda g: g.url == 'arthur').first()
            self.engine.cache.remove(gm)

        # GM can kick a single player from his game
        self.app.set_cookie('session', self.sid)
        ret = self.app.post('/vtt/kick-player/test-game-1/{0}'.format(player2.uuid), expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_cannot_kick_from_unknown_game(self):
        self.join_player('arthur', 'test-game-1', 'arthur', 'gold')
        ret2, player2 = self.join_player('arthur', 'test-game-1', 'bob', 'red')
        self.join_player('arthur', 'test-game-1', 'carlos', 'blue')
        self.join_player('arthur', 'test-game-1', 'blocker', 'green')

        with orm.db_session:
            gm_cache = self.engine.cache.get_from_url('arthur')
            game = gm_cache.db.Game.select(lambda g: g.url == 'test-game-1').first()
            gm_cache.remove(game)

        # GM can kick a single player from his game
        self.app.set_cookie('session', self.sid)
        ret = self.app.post('/vtt/kick-player/test-game-1/{0}'.format(player2.uuid), expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_GM_can_kick_players(self):
        self.join_player('arthur', 'test-game-1', 'arthur', 'gold')
        ret2, player2 = self.join_player('arthur', 'test-game-1', 'bob', 'red')
        self.join_player('arthur', 'test-game-1', 'carlos', 'blue')
        self.join_player('arthur', 'test-game-1', 'blocker', 'green')

        gm_cache = self.engine.cache.get_from_url('arthur')
        game_cache = gm_cache.get_from_url('test-game-1')
        self.assertEqual(len(game_cache.players), 4)

        # GM can kick a single player from his game
        self.app.set_cookie('session', self.sid)
        ret = self.app.post('/vtt/kick-player/test-game-1/{0}'.format(player2.uuid))
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(len(game_cache.players), 3)
        self.assertIn('arthur', game_cache.players)
        self.assertNotIn('bob', game_cache.players)
        self.assertIn('carlos', game_cache.players)
        gevent.kill(player2.greenlet)

    def test_GM_cannot_kick_player_from_unknown_game(self):
        ret1, player1 = self.join_player('arthur', 'test-game-1', 'arthur', 'gold')
        ret2, player2 = self.join_player('arthur', 'test-game-1', 'bob', 'red')
        ret3, player3 = self.join_player('arthur', 'test-game-1', 'carlos', 'blue')
        self.join_player('arthur', 'test-game-1', 'blocker', 'green')

        gm_cache = self.engine.cache.get_from_url('arthur')
        game_cache = gm_cache.get_from_url('test-game-1')
        self.assertEqual(len(game_cache.players), 4)

        self.app.set_cookie('session', self.sid)

        for p in [player1, player2, player3]:
            ret = self.app.post('/vtt/kick-player/test-weird-1/{0}'.format(p.uuid), expect_errors=True)
            self.assertEqual(ret.status_int, 404)
            self.assertEqual(len(game_cache.players), 4)

    def test_GM_can_kick_himself(self):
        ret1, player1 = self.join_player('arthur', 'test-game-1', 'arthur', 'gold')
        self.join_player('arthur', 'test-game-1', 'bob', 'red')
        self.join_player('arthur', 'test-game-1', 'carlos', 'blue')
        self.join_player('arthur', 'test-game-1', 'blocker', 'green')

        gm_cache = self.engine.cache.get_from_url('arthur')
        game_cache = gm_cache.get_from_url('test-game-1')
        self.assertEqual(len(game_cache.players), 4)

        self.app.set_cookie('session', self.sid)

        ret = self.app.post('/vtt/kick-player/test-game-1/{0}'.format(player1.uuid))
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(len(game_cache.players), 3)
        self.assertNotIn('arthur', game_cache.players)
        self.assertIn('carlos', game_cache.players)
        gevent.kill(player1.greenlet)

    def test_GM_can_kick_a_player_who_broke_pipe_and_went_offline(self):
        self.join_player('arthur', 'test-game-1', 'arthur', 'gold')
        ret2, player2 = self.join_player('arthur', 'test-game-1', 'bob', 'red')
        ret3, player3 = self.join_player('arthur', 'test-game-1', 'carlos', 'blue')
        self.join_player('arthur', 'test-game-1', 'blocker', 'green')

        gm_cache = self.engine.cache.get_from_url('arthur')
        game_cache = gm_cache.get_from_url('test-game-1')
        self.assertEqual(len(game_cache.players), 4)

        self.app.set_cookie('session', self.sid)

        ret = self.app.post('/vtt/kick-player/test-game-1/{0}'.format(player3.uuid))
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(len(game_cache.players), 3)
        gevent.kill(player2.greenlet)

    def test_GM_cannot_kick_a_player_twice(self):
        self.join_player('arthur', 'test-game-1', 'arthur', 'gold')
        self.join_player('arthur', 'test-game-1', 'bob', 'red')
        ret3, player3 = self.join_player('arthur', 'test-game-1', 'carlos', 'blue')
        self.join_player('arthur', 'test-game-1', 'blocker', 'green')

        gm_cache = self.engine.cache.get_from_url('arthur')
        game_cache = gm_cache.get_from_url('test-game-1')
        self.assertEqual(len(game_cache.players), 4)

        self.app.set_cookie('session', self.sid)

        ret = self.app.post('/vtt/kick-player/test-game-1/{0}'.format(player3.uuid))
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(len(game_cache.players), 3)

    def test_player_cannot_delete_game(self):
        gm_cache = self.engine.cache.get_from_url('arthur')

        ret = self.app.post('/vtt/delete-game/test-game-1', expect_errors=True)
        self.assertEqual(ret.status_int, 404)
        self.assertIsNotNone(gm_cache.get_from_url('test-game-1'))

    def test_GM_cannot_delete_unknown_game(self):
        gm_cache = self.engine.cache.get_from_url('arthur')

        self.app.set_cookie('session', self.sid)
        ret = self.app.post('/vtt/delete-game/test-weird-game', expect_errors=True)
        self.assertEqual(ret.status_int, 404)
        self.assertIsNotNone(gm_cache.get_from_url('test-game-1'))

    def test_GM_can_delete_his_game(self):
        gm_cache = self.engine.cache.get_from_url('arthur')

        self.app.set_cookie('session', self.sid)
        ret = self.app.post('/vtt/delete-game/test-game-1')
        self.assertEqual(ret.status_int, 200)
        self.assertIsNone(gm_cache.get_from_url('test-game-1'))

    def test_GM_cannot_delete_a_game_twice(self):
        self.app.set_cookie('session', self.sid)
        ret = self.app.post('/vtt/delete-game/test-game-1')
        self.assertEqual(ret.status_int, 200)
        ret = self.app.post('/vtt/delete-game/test-game-1', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_cannot_delete_game_for_unknown_gm(self):
        with orm.db_session:
            gm = self.engine.main_db.GM.select(lambda g: g.url == 'arthur').first()
            self.engine.cache.remove(gm)

        self.app.set_cookie('session', self.sid)
        ret = self.app.post('/vtt/delete-game/test-game-1', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_player_cannot_query_scenes(self):
        gm_ret, gm_player = self.join_player('arthur', 'test-game-1', 'arthur', 'gold')
        for i in range(3):
            gm_player.socket.push_receive({'OPID': 'GM-CREATE'})

        ret = self.app.post('/vtt/query-scenes/test-game-1', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_GM_cannot_query_scenes_from_unknown_game(self):
        gm_ret, gm_player = self.join_player('arthur', 'test-game-1', 'arthur', 'gold')
        for i in range(3):
            gm_player.socket.push_receive({'OPID': 'GM-CREATE'})

        self.app.set_cookie('session', self.sid)
        ret = self.app.post('/vtt/query-scenes/test-weird-game', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_GM_can_query_scenes_from_his_game(self):
        gm_ret, gm_player = self.join_player('arthur', 'test-game-1', 'arthur', 'gold')
        for i in range(3):
            gm_player.socket.push_receive({'OPID': 'GM-CREATE'})

        self.app.set_cookie('session', self.sid)
        ret = self.app.post('/vtt/query-scenes/test-game-1')
        self.assertEqual(ret.status_int, 200)

    def test_cannot_query_scenes_for_unknown_gm(self):
        with orm.db_session:
            gm = self.engine.main_db.GM.select(lambda g: g.url == 'arthur').first()
            self.engine.cache.remove(gm)

        self.app.set_cookie('session', self.sid)
        ret = self.app.post('/vtt/query-scenes/test-game-1', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_hashes_for_existing_assets(self):
        gm_ret, gm_player = self.join_player('arthur', 'test-game-1', 'arthur', 'gold')
        for i in range(3):
            gm_player.socket.push_receive({'OPID': 'GM-CREATE'})

        md5 = list(self.engine.storage.md5.checksums['arthur/test-game-1'].keys())[0]
        ret = self.app.post('/vtt/hashtest/arthur/test-game-1', {'hashs[]': [md5]}, xhr=True)
        self.assertEqual(ret.status_int, 200)
        expect = {
            "urls": ["/asset/arthur/test-game-1/0.png"]
        }
        self.assertEqual(ret.body, json.dumps(expect).encode('utf-8'))

    def test_cannot_hashtest_for_unknown_gm(self):
        ret = self.app.post('/vtt/hashtest/bob/test-game-1', {'hashs[]': []}, xhr=True, expect_errors=True)
        self.assertEqual(ret.status_int, 404)
    
    def test_cannot_hashtest_for_unknown_game(self):
        ret = self.app.post('/vtt/hashtest/arthur/test-game-2', {'hashs[]': []}, xhr=True, expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_cannot_hashtest_for_deleted_game(self):
        gm_cache = self.engine.cache.get_from_url('arthur')
        with orm.db_session:
            gm_cache.db.Game.select(lambda g: g.url == 'test-game-1').first().delete()

        ret = self.app.post('/vtt/hashtest/arthur/test-game-1', {'hashs[]': []}, xhr=True, expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_hashes_for_missing_assets(self):
        gm_ret, gm_player = self.join_player('arthur', 'test-game-1', 'arthur', 'gold')
        for i in range(3):
            gm_player.socket.push_receive({'OPID': 'GM-CREATE'})

        ret = self.app.post('/vtt/hashtest/arthur/test-game-1', {'hashs[]': ['deadneef']}, xhr=True)
        expect = {"urls": []}
        self.assertEqual(ret.body, json.dumps(expect).encode('utf-8'))
