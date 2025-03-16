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
        
    def tearDown(self):
        del self.db

    def test_id_from_filename(self) -> None:
        fname = '2.png'
        img_id = self.engine.storage.id_from_filename(fname)
        self.assertEqual(img_id, 2)

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
        files = set(self.engine.storage.get_all_images(game.gm_url, game.url))
        self.assertEqual(files, {'0.png', '1.png', '2.png', '3.png'})
      
    @db_session
    def test_to_md5_key(self):
        game = self.db.Game(url='foo', gm_url='url456')
        md5_key = self.engine.storage.md5.to_key(game.gm_url, game.url)
        self.assertEqual(md5_key, 'url456/foo')

    @db_session
    def test_get_next_id(self):
        game = self.db.Game(url='foo', gm_url='url456')
        game.post_setup()
        
        # starting id
        i = self.engine.storage.get_next_id(game.gm_url, game.url)
        self.assertEqual(i, 0)
        
        i = self.engine.storage.get_next_id(game.gm_url, game.url)
        self.assertEqual(i, 0)
        
        # gaps ignored for next_id
        img_path = self.engine.paths.get_game_path(game.gm_url, game.url)
        for i in [0, 1, 2, 3, 4, 6, 7, 8, 10, 11, 12]:
            p = img_path / '{0}.png'.format(i)
            p.touch()
        i = self.engine.storage.get_next_id(game.gm_url, game.url)
        self.assertEqual(i, 13)
        
        # first unused id
        p = img_path / '5.png'
        p.touch()     
        i = self.engine.storage.get_next_id(game.gm_url, game.url)
        self.assertEqual(i, 13)
    
    @db_session
    def test_make_md5s(self):
        game = self.db.Game(url='foo', gm_url='url456')
        game.post_setup()

        # create empty files (to mimic uploaded images)
        img_path = self.engine.paths.get_game_path(game.gm_url, game.url)
        id1 = self.engine.storage.get_next_id(game.gm_url, game.url)
        p1 = img_path / '{0}.png'.format(id1)
        p1.touch()
 
        # assume md5 file to be empty 
        md5_path = self.engine.paths.get_md5_path(game.gm_url, game.url)
        with open(md5_path, 'r') as handle:
            data = json.load(handle)
            self.assertEqual(len(data), 0)
        
        # assume empty cache
        md5_key = self.engine.storage.md5.to_key(game.gm_url, game.url)
        self.assertIn(md5_key, self.engine.storage.md5.checksums)
        cache_instance = self.engine.storage.md5.checksums[md5_key]
        self.assertEqual(len(cache_instance), 0)
        
        # create md5s
        self.engine.storage.init_game(game.gm_url, game.url)

        # expect md5 file with single hash
        self.assertTrue(os.path.exists(md5_path))
        with open(md5_path, 'r') as handle:
            data = json.load(handle)
            self.assertEqual(len(data), 1)

        # create more files
        id2 = self.engine.storage.get_next_id(game.gm_url, game.url)
        p2 = img_path / '{0}.png'.format(id2)
        with open(p2, 'w') as h:  # write different content because of hashing
            h.write('2')
        id3 = self.engine.storage.get_next_id(game.gm_url, game.url)
        p3 = img_path / '{0}.png'.format(id3)
        with open(p3, 'w') as h:  # write different content because of hashing
            h.write('3')
        id4 = self.engine.storage.get_next_id(game.gm_url, game.url)
        p4 = img_path / '{0}.png'.format(id4)
        with open(p4, 'w') as h:  # write different content because of hashing
            h.write('4')

        # update md5s
        self.engine.storage.init_game(game.gm_url, game.url)

        # expect md5 file with multiple hashs
        self.assertTrue(os.path.exists(md5_path))
        with open(md5_path, 'r') as handle:
            data = json.load(handle)
            self.assertEqual(len(data), 4)
        
        # test image IDs in cache
        md5_key = self.engine.storage.md5.to_key(game.gm_url, game.url)
        cache_instance = self.engine.storage.md5.checksums[md5_key]
        self.assertEqual(len(cache_instance), 4)
        ids = set()
        for md5 in cache_instance:
            img_id = cache_instance[md5]
            ids.add(img_id)
        self.assertEqual(ids, {0, 1, 2, 3})  # compare sets

        # delete file
        os.remove(p3)
        self.engine.storage.init_game(game.gm_url, game.url)
        md5_key = self.engine.storage.md5.to_key(game.gm_url, game.url)
        cache_instance = self.engine.storage.md5.checksums[md5_key]
        self.assertEqual(len(cache_instance), 3)

    @db_session
    def test_get_id_by_md5(self):
        game = self.db.Game(url='foo', gm_url='url456')
        game.post_setup()
        
        # create empty files (to mimic uploaded images)
        img_path = self.engine.paths.get_game_path(game.gm_url, game.url)
        id1 = self.engine.storage.get_next_id(game.gm_url, game.url)
        p1 = img_path / '{0}.png'.format(id1)
        with open(p1, 'w') as h:  # write different content because of hashing
            h.write('FOO')
        id2 = self.engine.storage.get_next_id(game.gm_url, game.url)
        p2 = img_path / '{0}.png'.format(id2)
        with open(p2, 'w') as h:  # write different content because of hashing
            h.write('A')
        id3 = self.engine.storage.get_next_id(game.gm_url, game.url)
        p3 = img_path / '{0}.png'.format(id3)
        with open(p3, 'w') as h:  # write different content because of hashing
            h.write('AAAA')
        id4 = self.engine.storage.get_next_id(game.gm_url, game.url)
        p4 = img_path / '{0}.png'.format(id4)
        with open(p4, 'w') as h:  # write different content because of hashing
            h.write('ABAAB')
        
        # assume empty cache
        md5_key = self.engine.storage.md5.to_key(game.gm_url, game.url)
        self.assertIn(md5_key, self.engine.storage.md5.checksums)
        cache_instance = self.engine.storage.md5.checksums[md5_key]
        self.assertEqual(len(cache_instance), 0)
        
        self.engine.storage.init_game(game.gm_url, game.url)

        # query 3rd image via checksum
        with open(p3, 'rb') as h:
            md5 = self.engine.storage.md5.generate(h)
        queried_id = self.engine.storage.md5.load(game.gm_url, game.url, md5)
        self.assertEqual(queried_id, id3)

        # query non-existing image  
        queried_id = self.engine.storage.md5.load(game.gm_url, game.url, 'foobar')
        self.assertIsNone(queried_id)

    @db_session
    def test_remove_md5(self):  
        game = self.db.Game(url='foo', gm_url='url456')
        game.post_setup()
        
        # create empty files (to mimic uploaded images)
        img_path = self.engine.paths.get_game_path(game.gm_url, game.url)
        id1 = self.engine.storage.get_next_id(game.gm_url, game.url)
        p1 = img_path / '{0}.png'.format(id1)
        with open(p1, 'w') as h:  # write different content because of hashing
            h.write('FOO')
        id2 = self.engine.storage.get_next_id(game.gm_url, game.url)
        p2 = img_path / '{0}.png'.format(id2)
        with open(p2, 'w') as h:  # write different content because of hashing
            h.write('A')
        id3 = self.engine.storage.get_next_id(game.gm_url, game.url)
        p3 = img_path / '{0}.png'.format(id3)
        with open(p3, 'w') as h:  # write different content because of hashing
            h.write('AAAA')
        id4 = self.engine.storage.get_next_id(game.gm_url, game.url)
        p4 = img_path / '{0}.png'.format(id4)
        with open(p4, 'w') as h:  # write different content because of hashing
            h.write('ABAAB')
        
        # assume empty cache
        md5_key = self.engine.storage.md5.to_key(game.gm_url, game.url)
        self.assertIn(md5_key, self.engine.storage.md5.checksums)
        cache_instance = self.engine.storage.md5.checksums[md5_key]
        self.assertEqual(len(cache_instance), 0)

        # create checksums
        self.engine.storage.init_game(game.gm_url, game.url)
        with open(p3, "rb") as handle:
            md5_3 = self.engine.storage.md5.generate(handle)
        queried_id = self.engine.storage.md5.load(game.gm_url, game.url, md5_3)
        self.assertEqual(queried_id, id3)

        # remove md5
        self.engine.storage.md5.delete(game.gm_url, game.url, id3)
        queried_id = self.engine.storage.md5.load(game.gm_url, game.url, md5_3)
        self.assertIsNone(queried_id)
