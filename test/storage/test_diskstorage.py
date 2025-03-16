"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2022 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import json
import os
import pathlib
import tempfile
import time
import zipfile

from PIL import Image
from bottle import FileUpload
from pony.orm import db_session

from test.common import EngineBaseTest
from vtt import orm, storage


class DiskStorageTest(EngineBaseTest):
    
    def setUp(self):
        super().setUp()
        
        # finish GM data
        with db_session:
            gm = self.engine.main_db.GM(name='user123', url='url456', identity='user123', sid='123456')
            gm.post_setup()
        
        # create GM database
        self.db = orm.create_gm_database(engine=self.engine, filename=':memory:')

        self.storage = storage.DiskStorage(self.engine.paths)
        
    def tearDown(self):
        del self.db

    @db_session
    def test_get_all_images(self):
        game = self.db.Game(url='foo', gm_url='url456')
        game.post_setup()
        
        # create empty files (to mimic uploaded images)
        img_path = self.engine.paths.get_game_path(game.gm_url, game.url)
        id1 = self.engine.storage.get_next_id(game.gm_url, game.url)
        p1 = img_path / '{0}.png'.format(id1)
        p1.touch()
        id2 = self.engine.storage.get_next_id(game.gm_url, game.url)
        p2 = img_path / '{0}.png'.format(id2)
        p2.touch()
        id3 = self.engine.storage.get_next_id(game.gm_url, game.url)
        p3 = img_path / '{0}.png'.format(id3)
        p3.touch()
        id4 = self.engine.storage.get_next_id(game.gm_url, game.url)
        p4 = img_path / '{0}.png'.format(id4)
        p4.touch()

        # create music file (not expected to be picked up)
        p5 = img_path / '2.mp3'
        p5.touch()
        
        # test files being detected
        files = set(self.storage.get_all_images(game.gm_url, game.url))
        self.assertEqual(files, {'0.png', '1.png', '2.png', '3.png'})
        

    """
    @db_session
    def test_upload(self):
        gm_url = 'url456'
        game = self.db.Game(url='foo', gm_url=gm_url)
        game.post_setup()
        
        self.db.Scene(game=game)
        
        # can upload image file
        pil_img = Image.new(mode='RGB', size=(32, 32))
        with tempfile.NamedTemporaryFile('wb') as wh:
            pil_img.save(wh.name, 'PNG')
            with open(wh.name, 'rb') as rh:
                # prepare fileupload
                fupload = FileUpload(rh, 'test.png', 'test.png')
                
                # test upload result
                old_id = self.engine.storage.get_next_id(game.gm_url, game.url)
                url = self.storage.upload_image(gm_url, game.url, fupload)

                new_id = self.engine.storage.get_next_id(game.gm_url, game.url)
                self.assertEqual(old_id + 1, new_id)
                self.assertEqual(url, game.get_image_url(old_id))
                
                # test file exists   
                img_path = self.engine.paths.get_game_path(game.gm_url, game.url)
                p = img_path / '{0}.png'.format(old_id)
                self.assertTrue(os.path.exists(p))
                
                # check md5 being stored
                md5 = self.storage.get_md5(fupload.file)
                checksums = self.storage.checksums[game.get_url()]
                self.assertIn(md5, checksums)
                
                # try to reupload file: same file used
                old_id = self.engine.storage.get_next_id(game.gm_url, game.url)
                new_url = self.storage.upload_image(gm_url, game.url, fupload)
                new_id = self.engine.storage.get_next_id(game.gm_url, game.url)
                self.assertEqual(old_id, new_id)
                self.assertEqual(url, new_url)
        
                # can upload another image file (different to 1st one)
                pil_img2 = Image.new(mode='RGB', size=(48, 48))
                with tempfile.NamedTemporaryFile('wb') as wh2:
                    pil_img2.save(wh2.name, 'PNG')
                    with open(wh2.name, 'rb') as rh2:
                        # upload 2nd file
                        fupload2 = FileUpload(rh2, 'test.png', 'test.png') 
                        new_id = self.engine.storage.get_next_id(game.gm_url, game.url)
                        self.storage.upload_image(gm_url, game.url, fupload2)
                        
                        # test 2nd file exists   
                        img_path2 = self.engine.paths.get_game_path(game.gm_url, game.url)
                        p2 = img_path2 / '{0}.png'.format(new_id)
                        self.assertTrue(os.path.exists(p2))
                        
                        # check 2nd md5 being stored
                        md5_2 = self.storage.get_md5(fupload2.file)
                        checksums = self.storage.checksums[game.get_url()]
                        self.assertIn(md5_2, checksums) 
                        
                        # cleanup to delete 1st file
                        b, r, t, m = game.cleanup(0)
                        self.assertGreater(b, 0)
                        self.assertEqual(r, 0)
                        self.assertEqual(t, 0)
                        self.assertEqual(m, 1)
                        checksums = self.storage.checksums[game.get_url()]
                        self.assertNotIn(md5, checksums)
                        self.assertFalse(os.path.exists(p))
                        self.assertIn(md5_2, checksums)
                        self.assertTrue(os.path.exists(p2))

                        # reupload 1st file            
                        p1_new = img_path2 / '{0}.png'.format(self.engine.storage.get_next_id(game.gm_url, game.url))
                        self.storage.upload_image(gm_url, game.url, fupload)
                        checksums = self.storage.checksums[game.get_url()]
                        self.assertIn(md5, checksums)
                        self.assertTrue(os.path.exists(p1_new))
                        self.assertIn(md5_2, checksums)
                        self.assertTrue(os.path.exists(p2))

        # cannot upload broken file
        with tempfile.NamedTemporaryFile('wb') as wh:
            wh.write(b'0' * 2**20)
            with open(wh.name, 'rb') as rh:
                # prepare fileupload
                fupload = FileUpload(rh, 'test.png', 'test.png')
                
                # test upload result
                self.engine.storage.get_next_id(game.gm_url, game.url)
                url = self.storage.upload_image(gm_url, game.url, fupload)
                self.assertIsNone(url)
    """
