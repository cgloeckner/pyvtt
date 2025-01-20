"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import json

from test.common import EngineBaseTest, make_image, make_zip
from vtt import routes


class GmImportRoutesTest(EngineBaseTest):

    def setUp(self):
        super().setUp()
        routes.register_gm(self.engine)
        routes.register_player(self.engine)
        routes.register_resources(self.engine)
        # @NOTE: custom error pages are not routed here

        # create some images
        self.img_small = make_image(512, 512)
        self.img_large = make_image(1500, 1500)
        self.img_huge = make_image(2000, 2000)
        mib = 2 ** 20
        self.assertLess(len(self.img_small), mib)
        self.assertLess(len(self.img_large), (self.engine.file_limit['background'] + 1) * mib)
        self.assertGreater(len(self.img_large), (self.engine.file_limit['background'] // 2) * mib)
        self.assertGreater(len(self.img_huge), self.engine.file_limit['background'] * mib)

        # create some zips
        empty_game = json.dumps({
            'tokens': [],
            'scenes': [{'tokens': [], 'backing': None}]
        })

        self.zip_normal = make_zip('zip2', empty_game, 5)
        self.zip_huge = make_zip('zip2', empty_game, self.engine.file_limit['game'])
        self.assertLess(len(self.zip_normal), self.engine.file_limit['game'] * mib)
        self.assertGreater(len(self.zip_huge), self.engine.file_limit['game'] * mib)
        self.fake_file = b'0' * mib
        self.text_file = b'hello world'

        # register
        ret = self.app.post('/vtt/join', {'gmname': 'arthur'}, xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.sid = self.app.cookies['session']
        self.app.reset()

    def test_cannot_import_from_image_without_GM_session(self):
        ret = self.app.post('/vtt/import-game/', upload_files=[('file', 'test.png', self.img_small)], xhr=True,
                            expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_cannot_import_from_zip_without_GM_session(self):
        ret = self.app.post('/vtt/import-game/', upload_files=[('file', 'test.zip', self.zip_normal)], xhr=True,
                            expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_cannot_import_from_image_with_invalid_GM_session(self):
        self.app.set_cookie('session', 'something-that-shall-fake-a-session')

        ret = self.app.post('/vtt/import-game/', upload_files=[('file', 'test.png', self.img_small)], xhr=True,
                            expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_cannot_import_from_zip_with_invalid_GM_session(self):
        self.app.set_cookie('session', 'something-that-shall-fake-a-session')

        ret = self.app.post('/vtt/import-game/', upload_files=[('file', 'test.zip', self.zip_normal)], xhr=True,
                            expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_can_import_from_image_with_auto_url(self):
        self.app.set_cookie('session', self.sid)

        ret = self.app.post('/vtt/import-game/', upload_files=[('file', 'test.png', self.img_small)], xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'application/json')
        self.assertTrue(ret.json['url_ok'])
        self.assertTrue(ret.json['file_ok'])
        self.assertEqual(ret.json['error'], '')
        self.assertEqual(len(ret.json['url'].split('/')), 3)
        self.assertEqual(ret.json['url'].split('/')[0], 'game')
        self.assertEqual(ret.json['url'].split('/')[1], 'arthur')

    def test_can_import_from_image_with_custom_url(self):
        self.app.set_cookie('session', self.sid)

        ret = self.app.post('/vtt/import-game/teSt-uRL-1', upload_files=[('file', 'test.png', self.img_small)],
                            xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'application/json')
        self.assertTrue(ret.json['url_ok'])
        self.assertTrue(ret.json['file_ok'])
        self.assertEqual(ret.json['error'], '')
        self.assertEqual(ret.json['url'], 'game/arthur/test-url-1')
        ret = self.app.get('/game/arthur/test-url-1')
        self.assertEqual(ret.status_int, 200)

    def test_cannot_import_from_image_with_existing_url(self):
        self.app.set_cookie('session', self.sid)

        self.app.post('/vtt/import-game/test-url-1', upload_files=[('file', 'test.png', self.img_small)], xhr=True)

        ret = self.app.post('/vtt/import-game/test-url-1', upload_files=[('file', 'test.png', self.img_small)],
                            xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'application/json')
        self.assertFalse(ret.json['url_ok'])
        self.assertEqual(ret.json['error'], 'ALREADY IN USE')
        self.assertEqual(ret.json['url'], '')

    def test_can_import_from_image_with_very_long_custom_url(self):
        self.app.set_cookie('session', self.sid)

        ret = self.app.post('/vtt/import-game/test-url-1-but-this-time-with-way-more-than-30-chars-total',
                            upload_files=[('file', 'test.png', self.img_small)], xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'application/json')
        self.assertTrue(ret.json['url_ok'])
        self.assertTrue(ret.json['file_ok'])
        self.assertEqual(ret.json['error'], '')
        self.assertEqual(ret.json['url'], 'game/arthur/test-url-1-but-this-time-with-')
        ret = self.app.get('/game/arthur/test-url-1-but-this-time-with-')
        self.assertEqual(ret.status_int, 200)

    def test_cannot_import_from_image_with_invalid_url(self):
        self.app.set_cookie('session', self.sid)

        ret = self.app.post('/vtt/import-game/test url-2', upload_files=[('file', 'test.png', self.img_small)],
                            xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'application/json')
        self.assertEqual(ret.json['error'], 'NO SPECIAL CHARS OR SPACES')
        self.assertEqual(ret.json['url'], '')
        self.assertFalse(ret.json['url_ok'])
        ret = self.app.get('/game/arthur/test url-2', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_can_import_from_multiple_files_at_once(self):
        self.app.set_cookie('session', self.sid)

        ret = self.app.post('/vtt/import-game/test-url-3', upload_files=[('file', 'test.png', self.img_small),
                                                                         ('file', 'test.png', self.img_small)],
                            xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'application/json')
        self.assertTrue(ret.json['url_ok'])
        self.assertFalse(ret.json['file_ok'])
        self.assertEqual(ret.json['error'], 'ONE FILE AT ONCE')
        ret = self.app.get('/game/arthur/test-url-3', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_can_import_from_large_image(self):
        self.app.set_cookie('session', self.sid)

        ret = self.app.post('/vtt/import-game/test-url-4', upload_files=[('file', 'test.png', self.img_large)],
                            xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'application/json')
        self.assertTrue(ret.json['url_ok'])
        self.assertTrue(ret.json['file_ok'])
        self.assertEqual(ret.json['error'], '')
        self.assertEqual(ret.json['url'], 'game/arthur/test-url-4')
        ret = self.app.get('/game/arthur/test-url-4')
        self.assertEqual(ret.status_int, 200)

    def test_cannot_import_from_too_large_image(self):
        self.app.set_cookie('session', self.sid)

        ret = self.app.post('/vtt/import-game/test-url-5', upload_files=[('file', 'test.png', self.img_huge)], xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'application/json')
        self.assertTrue(ret.json['url_ok'])
        self.assertFalse(ret.json['file_ok'])
        self.assertEqual(ret.json['error'],
                         'TOO LARGE BACKGROUND (MAX {0} MiB)'.format(self.engine.file_limit['background']))
        self.assertEqual(ret.json['url'], '')
        ret = self.app.get('/game/arthur/test-url-5', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_cannot_import_from_a_corrupt_zip_file(self):
        self.app.set_cookie('session', self.sid)

        ret = self.app.post('/vtt/import-game/test-url-6', upload_files=[('file', 'test.zip', self.fake_file)],
                            xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'application/json')
        self.assertTrue(ret.json['url_ok'])
        self.assertFalse(ret.json['file_ok'])
        self.assertEqual(ret.json['error'], 'CORRUPTED FILE')
        self.assertEqual(ret.json['url'], '')
        ret = self.app.get('/game/arthur/test-url-6', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_can_import_from_zip_file(self):
        self.app.set_cookie('session', self.sid)

        ret = self.app.post('/vtt/import-game/test-url-7', upload_files=[('file', 'test.zip', self.zip_normal)],
                            xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'application/json')
        self.assertTrue(ret.json['url_ok'])
        self.assertTrue(ret.json['file_ok'])
        self.assertEqual(ret.json['error'], '')
        ret = self.app.get('/game/arthur/test-url-7')
        self.assertEqual(ret.status_int, 200)

    def test_can_import_from_too_large_zip_file(self):
        self.app.set_cookie('session', self.sid)

        ret = self.app.post('/vtt/import-game/test-url-8', upload_files=[('file', 'test.zip', self.zip_huge)],
                            xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'application/json')
        self.assertTrue(ret.json['url_ok'])
        self.assertFalse(ret.json['file_ok'])
        self.assertEqual(ret.json['error'], 'TOO LARGE GAME (MAX {0} MiB)'.format(self.engine.file_limit['game']))
        ret = self.app.get('/game/arthur/test-url-8', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_can_import_from_unsupported_file_formats(self):
        self.app.set_cookie('session', self.sid)

        ret = self.app.post('/vtt/import-game/test-url-9', upload_files=[('file', 'test.txt', self.text_file)],
                            xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.content_type, 'application/json')
        self.assertTrue(ret.json['url_ok'])
        self.assertFalse(ret.json['file_ok'])
        self.assertEqual(ret.json['error'], 'USE AN IMAGE FILE')
        self.assertEqual(ret.json['url'], '')
        ret = self.app.get('/game/arthur/test-url-9', expect_errors=True)
        self.assertEqual(ret.status_int, 404)
