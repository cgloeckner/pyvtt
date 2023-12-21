"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import json
import os
import pathlib

from test.common import EngineBaseTest, make_image
from vtt import routes


def id_from_url(s: str) -> int:
    return int(s.split('/')[-1].split('.png')[0])


def count_mp3s(root: pathlib.Path):
    return len([f for f in os.listdir(root) if f.endswith('.mp3')])


class UploadRoutesTest(EngineBaseTest):

    def setUp(self):
        super().setUp()
        routes.register_gm(self.engine)
        routes.register_player(self.engine)
        routes.register_resources(self.engine)
        routes.register_api(self.engine)
        # @NOTE: custom error pages are not routed here

        # create some images
        self.img_small = make_image(512, 512)   # as token
        self.img_small2 = make_image(256, 256)
        self.img_small3 = make_image(633, 250)
        self.img_small4 = make_image(233, 240)
        self.img_large = make_image(1500, 1500)  # as background
        self.img_huge = make_image(2000, 2000)  # too large
        mib = 2 ** 20
        self.assertLess(len(self.img_small), mib)
        self.assertLess(len(self.img_large), (self.engine.file_limit['background'] + 1) * mib)
        self.assertGreater(len(self.img_large), (self.engine.file_limit['background'] // 2) * mib)
        self.assertGreater(len(self.img_huge), self.engine.file_limit['background'] * mib)

        # register arthur
        ret = self.app.post('/vtt/join', {'gmname': 'arthur'}, xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.sid = self.app.cookies['session']

        # create a game
        self.img_small = make_image(512, 512)
        ret = self.app.post('/vtt/import-game/test-game-1', upload_files=[('file', 'test.png', self.img_small)],
                            xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.app.reset()

    def test_can_upload_token_in_existing_game(self):
        ret = self.app.post('/game/arthur/test-game-1/upload',
                            upload_files=[
                                ('file[]', 'test.png', self.img_small2),
                                ('file[]', 'another.png', self.img_small3)
                            ], xhr=True)
        self.assertEqual(ret.status_int, 200)
        # @NOTE: non-json response but with json-dumped data
        # I need to find a way to answer with a json-response to an
        # upload post (from jQuery)
        data = json.loads(ret.body)
        self.assertEqual(len(data['urls']), 2)
        self.assertFalse(data['music'])
        self.assertEqual(id_from_url(data['urls'][0]), 1)  # since 0 is background
        self.assertEqual(id_from_url(data['urls'][1]), 2)

    def test_reuploading_image_will_return_existing_urls_instead_of_new_ones(self):
        ret1 = self.app.post('/game/arthur/test-game-1/upload',
                             upload_files=[
                                 ('file[]', 'test.png', self.img_small2),
                                 ('file[]', 'another.png', self.img_small3)
                             ], xhr=True)
        self.assertEqual(ret1.status_int, 200)

        ret2 = self.app.post('/game/arthur/test-game-1/upload',
                             upload_files=[
                                 ('file[]', 'test.png', self.img_small2),
                                 ('file[]', 'another.bmp', self.img_small3),
                                 ('file[]', 'foo.png', self.img_small3),
                                 ('file[]', 'random.tiff', self.img_small3),
                                 ('file[]', 'something.gif', self.img_small2),
                                 ('file[]', 'weird.jpg', self.img_small3)
                             ], xhr=True)
        self.assertEqual(ret2.status_int, 200)
        data = json.loads(ret2.body)
        self.assertEqual(len(data['urls']), 6)
        self.assertFalse(data['music'])
        self.assertEqual(id_from_url(data['urls'][0]), 1)
        self.assertEqual(id_from_url(data['urls'][1]), 2)
        self.assertEqual(id_from_url(data['urls'][2]), 2)
        self.assertEqual(id_from_url(data['urls'][3]), 2)
        self.assertEqual(id_from_url(data['urls'][4]), 1)
        self.assertEqual(id_from_url(data['urls'][5]), 2)

    def test_uploads_with_too_large_images_are_ignored_completly(self):
        images = os.listdir(self.engine.paths.get_game_path('arthur', 'test-game-1'))
        self.assertEqual(len(images), 2)  # background + md5-file
        ret = self.app.post('/game/arthur/test-game-1/upload',
                            upload_files=[
                                ('file[]', 'another.jpg', self.img_small4),
                                ('file[]', 'test.png', self.img_large),
                                ('file[]', 'another.jpg', self.img_small4)
                            ], xhr=True, expect_errors=True)
        self.assertEqual(ret.status_int, 403)
        # expect no new images in directory
        images = os.listdir(self.engine.paths.get_game_path('arthur', 'test-game-1'))
        self.assertEqual(len(images), 2)  # background + md5-file
        self.assertIn('0.png', images)
        self.assertNotIn('1.png', images)

    def test_can_upload_background_and_tokens_to_new_scene(self):
        gm_cache = self.engine.cache.get_from_url('arthur')
        game_cache = gm_cache.get_from_url('test-game-1')
        gm_player = game_cache.insert('GM Arthur', 'red', True)
        game_cache.on_create_scene(gm_player, {})
        ret = self.app.post('/game/arthur/test-game-1/upload',
                            upload_files=[
                                ('file[]', 'test.png', self.img_large),
                                ('file[]', 'another.jpg', self.img_small2),
                                ('file[]', 'another.jpg', self.img_small3)
                            ], xhr=True, expect_errors=True)
        self.assertEqual(ret.status_int, 200)
        data = json.loads(ret.body)
        self.assertEqual(len(data['urls']), 3)
        self.assertFalse(data['music'])
        self.assertEqual(id_from_url(data['urls'][0]), 1)
        self.assertEqual(id_from_url(data['urls'][1]), 2)
        self.assertEqual(id_from_url(data['urls'][2]), 3)

    def test_cannot_upload_backgrounds_that_are_too_large(self):
        # cannot upload huge image as background
        gm_cache = self.engine.cache.get_from_url('arthur')
        game_cache = gm_cache.get_from_url('test-game-1')
        gm_player = game_cache.insert('GM Arthur', 'red', True)
        game_cache.on_create_scene(gm_player, {})
        ret = self.app.post('/game/arthur/test-game-1/upload',
                            upload_files=[
                                ('file[]', 'test.png', self.img_huge)
                            ], xhr=True, expect_errors=True)
        self.assertEqual(ret.status_int, 403)

    def test_cannot_upload_image_to_unknown_game(self):
        ret = self.app.post('/game/arthur/test-game-1456/upload',
                            upload_files=[
                                ('file[]', 'test.png', self.img_small2),
                                ('file[]', 'another.png', self.img_small3)
                            ], xhr=True, expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_cannot_upload_image_to_unknown_GM(self):
        # cannot upload image to unknown GM
        ret = self.app.post('/game/bob/test-game-1/upload',
                            upload_files=[
                                ('file[]', 'test.png', self.img_small2),
                                ('file[]', 'another.png', self.img_small3)
                            ], xhr=True, expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_cannot_upload_unsupported_mime_type(self):
        ret = self.app.post('/game/arthur/test-game-1/upload',
                            upload_files=[
                                ('file[]', 'test.png', self.img_small2),
                                ('file[]', 'foo.exe', b''),
                                ('file[]', 'another.png', self.img_small3)
                            ], xhr=True, expect_errors=True)
        self.assertEqual(ret.status_int, 403)

    def test_can_upload_music(self):
        root = self.engine.paths.get_game_path('arthur', 'test-game-1')

        self.assertEqual(count_mp3s(root), 0)
        ret = self.app.post('/game/arthur/test-game-1/upload',
                            upload_files=[
                                ('file[]', 'sample.mp3', b'')
                            ], xhr=True)
        self.assertEqual(ret.status_int, 200)
        data = json.loads(ret.body)
        self.assertEqual(len(data['urls']), 0)
        self.assertEqual(data['music'], [0])
        self.assertEqual(count_mp3s(root), 1)

    def test_can_upload_multiple_tracks_at_once(self):
        root = self.engine.paths.get_game_path('arthur', 'test-game-1')

        ret = self.app.post('/game/arthur/test-game-1/upload',
                            upload_files=[
                                ('file[]', 'sample.mp3', b''),
                                ('file[]', 'foo.mp3', b''),
                                ('file[]', 'three.mp3', b'')
                            ], xhr=True)
        self.assertEqual(ret.status_int, 200)
        data = json.loads(ret.body)
        self.assertEqual(len(data['urls']), 0)
        self.assertEqual(data['music'], [0, 1, 2])
        self.assertEqual(count_mp3s(root), 3)

    def test_can_upload_music_and_images_at_once(self):
        root = self.engine.paths.get_game_path('arthur', 'test-game-1')

        ret = self.app.post('/game/arthur/test-game-1/upload',
                            upload_files=[
                                ('file[]', 'test.png', self.img_small2),
                                ('file[]', 'sample.mp3', b''),
                                ('file[]', 'another.png', self.img_small3)
                            ], xhr=True)
        self.assertEqual(ret.status_int, 200)
        data = json.loads(ret.body)
        self.assertEqual(len(data['urls']), 2)
        self.assertEqual(id_from_url(data['urls'][0]), 1)
        self.assertEqual(id_from_url(data['urls'][1]), 2)
        self.assertEqual(data['music'], [0])
        self.assertEqual(count_mp3s(root), 1)

    def test_cannot_upload_more_music_than_slots_are_available(self):
        root = self.engine.paths.get_game_path('arthur', 'test-game-1')

        self.assertEqual(self.engine.file_limit['num_music'], 5)
        ret = self.app.post('/game/arthur/test-game-1/upload',
                            upload_files=[
                                ('file[]', 'sample.mp3', b''),
                                ('file[]', 'foo.mp3', b'')
                            ], xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(count_mp3s(root), 2)

    def test_players_cannot_upload_background_as_game(self):
        ret = self.app.post('/vtt/upload-background/arthur/test-game-1',
                            upload_files=[('file[]', 'back.png', self.img_large)], xhr=True, expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_GM_can_upload_background(self):
        self.app.set_cookie('session', self.sid)

        ret = self.app.post('/vtt/upload-background/arthur/test-game-1',
                            upload_files=[('file[]', 'back.png', self.img_large)], xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(id_from_url(str(ret.body)), 1)

    def test_GM_cannot_upload_multiple_backgrounds(self):
        self.app.set_cookie('session', self.sid)

        ret = self.app.post('/vtt/upload-background/arthur/test-game-1',
                            upload_files=[
                                ('file[]', 'back.png', self.img_large),
                                ('file[]', 'back2.png', self.img_large)
                            ], xhr=True, expect_errors=True)
        self.assertEqual(ret.status_int, 403)

    def test_GM_cannot_upload_too_large_background(self):
        self.app.set_cookie('session', self.sid)

        ret = self.app.post('/vtt/upload-background/arthur/test-game-1',
                            upload_files=[('file[]', 'back.png', self.img_huge)], xhr=True, expect_errors=True)
        self.assertEqual(ret.status_int, 403)
