"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2024 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import shutil
import json

from test.common import EngineBaseTest, make_image
from vtt import routes


class AssetRoutesTest(EngineBaseTest):

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

        # create two games
        img_small = make_image(512, 512)
        ret = self.app.post('/vtt/import-game/test-game-1', upload_files=[('file', 'test.png', img_small)], xhr=True)
        self.assertEqual(ret.status_int, 200)
        ret = self.app.post('/vtt/import-game/test-game-2', upload_files=[('file', 'test.png', img_small)], xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.app.reset()

        # create more images
        self.img_path = self.engine.paths.get_game_path('arthur', 'test-game-1')
        shutil.copyfile(self.img_path / '0.png', self.img_path / '1.png')

    def test_can_access_default_static_assets(self):
        ret = self.app.get('/static/assets/heart.png')
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'image/png')

    def test_can_access_custom_static_assets(self):
        ret = self.app.get('/static/assets/new.png', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

        custom_assets_root = self.engine.paths.get_assets_path()
        new_asset = custom_assets_root / 'new.png'
        new_asset.touch()

        ret = self.app.get('/static/assets/new.png')
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'image/png')

    def test_can_query_image_assets(self):
        ret = self.app.get('/asset/arthur/test-game-1/0.png')
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'image/png')

        ret = self.app.get('/asset/arthur/test-game-1/1.png')
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'image/png')

    def test_cannot_query_unknown_image_asset(self):
        ret = self.app.get('/asset/arthur/test-game-2/2.png', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_can_query_image_asset_from_another_game(self):
        ret = self.app.get('/asset/arthur/test-game-2/0.png')
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'image/png')

    def test_can_query_image_asset_from_an_unknown_game(self):
        ret = self.app.get('/asset/arthur/test-game-3/0.png', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_can_query_image_asset_from_an_unknown_GM(self):
        ret = self.app.get('/asset/carlos/test-game-3/0.png', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_can_query_GM_database_files(self):
        ret = self.app.get('/asset/arthur/test-game-1/../gm.db', expect_errors=True)
        self.assertEqual(ret.status_int, 404)
        ret = self.app.get('/asset/arthur/test-game-1/../&#47;m.db', expect_errors=True)
        self.assertEqual(ret.status_int, 404)
        ret = self.app.get('/asset/arthur/../gm.db', expect_errors=True)
        self.assertEqual(ret.status_int, 404)
        ret = self.app.get('/asset/arthur/test-game-1/"../gm.db"', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_can_query_image_non_image_assets(self):
        with open(self.img_path / 'test.txt', 'w') as h:
            h.write('hello world')
        ret = self.app.get('/asset/arthur/test-game-1/test.txt', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_can_only_query_music_asset_from_existing_slots(self):
        ret = self.app.post('/game/arthur/test-game-1/upload',
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
            ret = self.app.get('/asset/arthur/test-game-1/{0}.mp3?update=0815'.format(slot_id))
            self.assertEqual(ret.status_int, 200)

        # cannot query invalid slot
        ret = self.app.get('/asset/arthur/test-game-1/14.mp3?update=0815', expect_errors=True)
        self.assertEqual(ret.status_int, 404)
