"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import os
import shutil

from test.common import EngineBaseTest, make_image
from vtt import routes


class ResourcesRoutesTest(EngineBaseTest):

    def setUp(self):
        super().setUp()
        routes.register_gm(self.engine)
        routes.register_player(self.engine)
        routes.register_resources(self.engine)
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

    def test_cannot_load_non_existing_file(self):
        ret = self.app.get('/static/fantasy-file.txt', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_can_load_custom_static_file(self):
        ret = self.app.get('/static/malicious.js', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

        default_static_root = self.engine.paths.get_static_path()
        new_file = default_static_root / 'malicious.js'
        new_file.touch()
        ret = self.app.get('/static/malicious.js')
        self.assertEqual(ret.status_int, 200)
        self.assertIn('javascript', ret.content_type)

    def test_can_load_existing_png(self):
        ret = self.app.get('/static/d20.png')
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'image/png')

    def test_can_load_existing_jpg(self):
        ret = self.app.get('/static/background.jpg')
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'image/jpeg')

    def test_can_load_favicon(self):
        ret = self.app.get('/static/favicon.ico')
        self.assertEqual(ret.status_int, 200)
        self.assertIn('icon', ret.content_type)

    def test_can_load_existing_javascript_file(self):
        ret = self.app.get('/static/client/render.js')
        self.assertEqual(ret.status_int, 200)
        self.assertIn('javascript', ret.content_type)

    def test_can_load_existing_css_file(self):
        ret = self.app.get('/static/client/layout.css')
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'text/css')

    def test_cannot_query_into_parent_directory(self):
        ret = self.app.get('/static/../README.md/0', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_cannot_query_into_non_supported_sub_directory(self):
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
