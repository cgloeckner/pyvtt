"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

from test.common import EngineBaseTest, make_image
from vtt import routes, orm


class ThumbnailRoutesTest(EngineBaseTest):

    def setUp(self):
        super().setUp()
        routes.register_gm(self.engine)
        routes.register_player(self.engine)
        routes.register_resources(self.engine)
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

    def test_can_query_game_thumbnail(self):
        ret = self.app.get('/vtt/thumbnail/arthur/test-game-1')
        self.assertEqual(ret.status_int, 302)
        ret = ret.follow()
        self.assertEqual(ret.status_int, 302)
        ret = ret.follow()
        self.assertEqual(ret.content_type, 'image/png')

    def test_cannot_query_unknown_gm_thumbnail(self):
        ret = self.app.get('/vtt/thumbnail/bob/test-game-1', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_cannot_query_unknown_game_thumbnail(self):
        ret = self.app.get('/vtt/thumbnail/arthur/test-game-123', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_can_query_game_scene_thumbnail(self):
        ret = self.app.get('/vtt/thumbnail/arthur/test-game-1/1')
        self.assertEqual(ret.status_int, 302)
        ret = ret.follow()
        self.assertEqual(ret.content_type, 'image/png')

    def test_cannot_query_known_games_unknown_scene_thumbnail(self):
        ret = self.app.get('/vtt/thumbnail/arthur/test-game-1/7', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_cannot_query_unknown_games_scene_thumbnail(self):
        ret = self.app.get('/vtt/thumbnail/arthur/test-game-123/7', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_cannot_query_unknown_gms_scene_thumbnail(self):
        ret = self.app.get('/vtt/thumbnail/bob/test-game-1/1', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_can_query_game_scene_thumbnail_if_no_background_was_set(self):
        gm_cache = self.engine.cache.get_from_url('arthur')
        with orm.db_session:
            scene = gm_cache.db.Scene.select(lambda scn: scn.id == 1 and scn.game.url == 'test-game-1').first()
            scene.backing = None

        ret = self.app.get('/vtt/thumbnail/arthur/test-game-1/1')
        self.assertEqual(ret.status_int, 302)
        ret = ret.follow()
        self.assertEqual(ret.content_type, 'image/jpeg')
