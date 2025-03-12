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
from vtt import orm


class GameTest(EngineBaseTest):
    
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

    @db_session
    def test_mayExpireSoon(self):
        game = self.db.Game(url='foo', gm_url='url456')
        game.post_setup()
        now = int(time.time())

        # will expire soon
        game.timeid = int(now - self.engine.cleanup['expire'] * 0.75)
        self.assertTrue(game.may_expire_soon(now))

        # will not expire soon
        game.timeid = int(now - self.engine.cleanup['expire'] * 0.3)
        self.assertFalse(game.may_expire_soon(now))
        
        # even HAS expired
        game.timeid = int(now - self.engine.cleanup['expire'] * 1.2)
        self.assertTrue(game.may_expire_soon(now))
        
    @db_session
    def test_hasExpired(self):
        game = self.db.Game(url='foo', gm_url='url456') 
        game.post_setup()
        now = int(time.time())

        # has not expired yet
        game.timeid = int(now - self.engine.cleanup['expire'] * 0.75)
        self.assertFalse(game.has_expired(now))

        # has expired
        game.timeid = int(now - self.engine.cleanup['expire'] * 1.2)
        self.assertTrue(game.has_expired(now))
        
    @db_session
    def test_getUrl(self):
        game = self.db.Game(url='foo', gm_url='url456')
        url = game.get_url()
        self.assertEqual(url, 'url456/foo')
        
    @db_session
    def test_makeMd5s(self):
        game = self.db.Game(url='foo', gm_url='url456')
        game.post_setup()

        # create empty files (to mimic uploaded images)
        img_path = self.engine.paths.get_game_path(game.gm_url, game.url)
        id1 = game.get_next_id()
        p1 = img_path / '{0}.png'.format(id1)
        p1.touch()

        # assume md5 file to be empty 
        md5_path = self.engine.paths.get_md5_path(game.gm_url, game.url)
        with open(md5_path, 'r') as handle:
            data = json.load(handle)
            self.assertEqual(len(data), 0)
        
        # assume empty cache
        cache_instance = self.engine.checksums[game.get_url()]
        self.assertEqual(len(cache_instance), 0)
        
        # create md5s
        game.make_md5s()

        # expect md5 file with single hash
        self.assertTrue(os.path.exists(md5_path))
        with open(md5_path, 'r') as handle:
            data = json.load(handle)
            self.assertEqual(len(data), 1)

        # create more files
        id2 = game.get_next_id()
        p2 = img_path / '{0}.png'.format(id2)
        with open(p2, 'w') as h:  # write different content because of hashing
            h.write('2')
        id3 = game.get_next_id()
        p3 = img_path / '{0}.png'.format(id3)
        with open(p3, 'w') as h:  # write different content because of hashing
            h.write('3')
        id4 = game.get_next_id()
        p4 = img_path / '{0}.png'.format(id4)
        with open(p4, 'w') as h:  # write different content because of hashing
            h.write('4')

        # update md5s
        game.make_md5s()

        # expect md5 file with multiple hashs
        self.assertTrue(os.path.exists(md5_path))
        with open(md5_path, 'r') as handle:
            data = json.load(handle)
            self.assertEqual(len(data), 4)
        
        # test image IDs in cache
        cache_instance = self.engine.checksums[game.get_url()]
        self.assertEqual(len(cache_instance), 4)
        ids = set()
        for md5 in cache_instance:
            img_id = cache_instance[md5]
            ids.add(img_id)
        self.assertEqual(ids, {0, 1, 2, 3})  # compare sets

        # delete file
        os.remove(p3)
        game.make_md5s()
        cache_instance = self.engine.checksums[game.get_url()]
        self.assertEqual(len(cache_instance), 3)

    @db_session
    def test_getIdByMd5(self):
        game = self.db.Game(url='foo', gm_url='url456')
        game.post_setup()
        
        # create empty files (to mimic uploaded images)
        img_path = self.engine.paths.get_game_path(game.gm_url, game.url)
        id1 = game.get_next_id()
        p1 = img_path / '{0}.png'.format(id1)
        with open(p1, 'w') as h:  # write different content because of hashing
            h.write('FOO')
        id2 = game.get_next_id()
        p2 = img_path / '{0}.png'.format(id2)
        with open(p2, 'w') as h:  # write different content because of hashing
            h.write('A')
        id3 = game.get_next_id()
        p3 = img_path / '{0}.png'.format(id3)
        with open(p3, 'w') as h:  # write different content because of hashing
            h.write('AAAA')
        id4 = game.get_next_id()
        p4 = img_path / '{0}.png'.format(id4)
        with open(p4, 'w') as h:  # write different content because of hashing
            h.write('ABAAB')
        
        # assume empty cache
        cache_instance = self.engine.checksums[game.get_url()]
        self.assertEqual(len(cache_instance), 0)
        
        game.make_md5s()

        # query 3rd image via checksum
        with open(p3, 'rb') as h:
            md5 = self.engine.get_md5(h)
        queried_id = game.get_id_by_md5(md5)
        self.assertEqual(queried_id, id3)

        # query non-existing image  
        queried_id = game.get_id_by_md5('foobar')
        self.assertIsNone(queried_id)

    @db_session
    def test_removeMd5(self):  
        game = self.db.Game(url='foo', gm_url='url456')
        game.post_setup()
        
        # create empty files (to mimic uploaded images)
        img_path = self.engine.paths.get_game_path(game.gm_url, game.url)
        id1 = game.get_next_id()
        p1 = img_path / '{0}.png'.format(id1)
        with open(p1, 'w') as h:  # write different content because of hashing
            h.write('FOO')
        id2 = game.get_next_id()
        p2 = img_path / '{0}.png'.format(id2)
        with open(p2, 'w') as h:  # write different content because of hashing
            h.write('A')
        id3 = game.get_next_id()
        p3 = img_path / '{0}.png'.format(id3)
        with open(p3, 'w') as h:  # write different content because of hashing
            h.write('AAAA')
        id4 = game.get_next_id()
        p4 = img_path / '{0}.png'.format(id4)
        with open(p4, 'w') as h:  # write different content because of hashing
            h.write('ABAAB')
        
        # assume empty cache
        cache_instance = self.engine.checksums[game.get_url()]
        self.assertEqual(len(cache_instance), 0)

        # create checksums
        game.make_md5s()
        with open(p3, "rb") as handle:
            md5_3 = self.engine.get_md5(handle)
        queried_id = game.get_id_by_md5(md5_3)
        self.assertEqual(queried_id, id3)

        # remove md5
        game.remove_md5(id3)
        queried_id = game.get_id_by_md5(md5_3)
        self.assertIsNone(queried_id)
    
    @db_session
    def test_postSetup(self):
        game = self.db.Game(url='foo', gm_url='url456')
        
        game_path = self.engine.paths.get_game_path(gm=game.gm_url, game=game.url)

        # assume no md5 file yet
        md5_path = self.engine.paths.get_md5_path(game.gm_url, game.url)
        self.assertFalse(os.path.exists(md5_path))
        
        # test game setup
        self.assertFalse(os.path.isdir(game_path))
        game.post_setup()
        self.assertTrue(os.path.isdir(game_path))

        # test scene ordering
        self.assertEqual(game.order, list())

        # assume existing md5 file yet
        self.assertTrue(os.path.exists(md5_path))

    @db_session
    def test_reorderScenes(self):
        game = self.db.Game(url='foo', gm_url='url456')
        for i in range(4):
            last_scene = self.db.Scene(game=game)
        self.db.commit()

        # expect no order list yet
        self.assertEqual(game.order, list())

        game.reorder_scenes()
        
        # expect ordered by IDs
        last_id = last_scene.id
        self.assertEqual(game.order, [last_id-3, last_id-2, last_id-1, last_id])
    
    @db_session
    def test_getAllImages(self):
        game = self.db.Game(url='foo', gm_url='url456')
        game.post_setup()
        
        # create empty files (to mimic uploaded images)
        img_path = self.engine.paths.get_game_path(game.gm_url, game.url)
        id1 = game.get_next_id()
        p1 = img_path / '{0}.png'.format(id1)
        p1.touch()
        id2 = game.get_next_id()
        p2 = img_path / '{0}.png'.format(id2)
        p2.touch()
        id3 = game.get_next_id()
        p3 = img_path / '{0}.png'.format(id3)
        p3.touch()
        id4 = game.get_next_id()
        p4 = img_path / '{0}.png'.format(id4)
        p4.touch()

        # create music file (not expected to be picked up)
        p5 = img_path / '2.mp3'
        p5.touch()
        
        # test files being detected
        files = set(game.get_all_images())
        self.assertEqual(files, {'0.png', '1.png', '2.png', '3.png'})
        
    @db_session
    def test_getNextId(self):
        game = self.db.Game(url='foo', gm_url='url456')
        game.post_setup()
        
        # starting id
        i = game.get_next_id()
        self.assertEqual(i, 0)
        
        i = game.get_next_id()
        self.assertEqual(i, 0)
        
        # gaps ignored for next_id
        img_path = self.engine.paths.get_game_path(game.gm_url, game.url)
        for i in [0, 1, 2, 3, 4, 6, 7, 8, 10, 11, 12]:
            p = img_path / '{0}.png'.format(i)
            p.touch()
        i = game.get_next_id()
        self.assertEqual(i, 13)
        
        # first unused id
        p = img_path / '5.png'
        p.touch()     
        i = game.get_next_id()
        self.assertEqual(i, 13)
    
    @db_session
    def test_getImageUrl(self):
        game = self.db.Game(url='foo', gm_url='url456')
        game.post_setup()
        
        url = game.get_image_url(17)
        self.assertEqual(url, '/asset/url456/foo/17.png')
        
    @db_session
    def test_getFileSize(self):
        game = self.db.Game(url='foo', gm_url='url456')
        game.post_setup()
        
        # create empty files (to mimic uploaded images)
        img_path = self.engine.paths.get_game_path(game.gm_url, game.url)
        id1 = game.get_next_id()
        p1 = img_path / '{0}.png'.format(id1)
        p1.touch()
        id2 = game.get_next_id()
        p2 = img_path / '{0}.png'.format(id2)
        with open(p2, 'w') as h:
            h.write('test')
        id3 = game.get_next_id()
        p3 = img_path / '{0}.png'.format(id3)
        with open(p3, 'w') as h:
            h.write('xy')
        id4 = game.get_next_id()
        p4 = img_path / '{0}.png'.format(id4)
        with open(p4, 'w') as h:
            h.write('abc')
        
        # test file sizes
        size1 = game.get_file_size(str(p1))
        size2 = game.get_file_size(str(p2))
        size3 = game.get_file_size(str(p3))
        size4 = game.get_file_size(str(p4))
        self.assertEqual(size1, 0)
        self.assertEqual(size2, 4)
        self.assertEqual(size3, 2)
        self.assertEqual(size4, 3)
        
    @db_session
    def test_upload(self):
        game = self.db.Game(url='foo', gm_url='url456')
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
                old_id = game.get_next_id()
                url = game.upload(fupload)

                new_id = game.get_next_id()
                self.assertEqual(old_id + 1, new_id)
                self.assertEqual(url, game.get_image_url(old_id))
                
                # test file exists   
                img_path = self.engine.paths.get_game_path(game.gm_url, game.url)
                p = img_path / '{0}.png'.format(old_id)
                self.assertTrue(os.path.exists(p))
                
                # check md5 being stored
                md5 = self.engine.get_md5(fupload.file)
                checksums = self.engine.checksums[game.get_url()]
                self.assertIn(md5, checksums)
                
                # try to reupload file: same file used
                old_id = game.get_next_id()
                new_url = game.upload(fupload)
                new_id = game.get_next_id()
                self.assertEqual(old_id, new_id)
                self.assertEqual(url, new_url)
        
                # can upload another image file (different to 1st one)
                pil_img2 = Image.new(mode='RGB', size=(48, 48))
                with tempfile.NamedTemporaryFile('wb') as wh2:
                    pil_img2.save(wh2.name, 'PNG')
                    with open(wh2.name, 'rb') as rh2:
                        # upload 2nd file
                        fupload2 = FileUpload(rh2, 'test.png', 'test.png') 
                        new_id = game.get_next_id()
                        game.upload(fupload2)
                        
                        # test 2nd file exists   
                        img_path2 = self.engine.paths.get_game_path(game.gm_url, game.url)
                        p2 = img_path2 / '{0}.png'.format(new_id)
                        self.assertTrue(os.path.exists(p2))
                        
                        # check 2nd md5 being stored
                        md5_2 = self.engine.get_md5(fupload2.file)
                        checksums = self.engine.checksums[game.get_url()]
                        self.assertIn(md5_2, checksums) 
                        
                        # cleanup to delete 1st file
                        b, r, t, m = game.cleanup(0)
                        self.assertGreater(b, 0)
                        self.assertEqual(r, 0)
                        self.assertEqual(t, 0)
                        self.assertEqual(m, 1)
                        checksums = self.engine.checksums[game.get_url()]
                        self.assertNotIn(md5, checksums)
                        self.assertFalse(os.path.exists(p))
                        self.assertIn(md5_2, checksums)
                        self.assertTrue(os.path.exists(p2))

                        # reupload 1st file            
                        p1_new = img_path2 / '{0}.png'.format(game.get_next_id())
                        game.upload(fupload)
                        checksums = self.engine.checksums[game.get_url()]
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
                game.get_next_id()
                url = game.upload(fupload)
                self.assertIsNone(url)
        
    def test_getIdFromUrl(self):
        self.assertEqual(self.db.Game.get_id_from_url('/foo/bar/3.17.png'), 3)
        self.assertEqual(self.db.Game.get_id_from_url('/0.'), 0)
        with self.assertRaises(ValueError):
            self.db.Game.get_id_from_url('/a.')
        
    @db_session
    def test_getAbandonedImages(self):
        game = self.db.Game(url='foo', gm_url='url456')
        game.post_setup()
        
        # create empty files (to mimic uploaded images)
        img_path = self.engine.paths.get_game_path(game.gm_url, game.url)
        id1 = game.get_next_id()
        p1 = img_path / '{0}.png'.format(id1)
        p1.touch()
        id2 = game.get_next_id()
        p2 = img_path / '{0}.png'.format(id2)
        p2.touch()
        id3 = game.get_next_id()
        p3 = img_path / '{0}.png'.format(id3)
        p3.touch()
        id4 = game.get_next_id()
        p4 = img_path / '{0}.png'.format(id4)
        p4.touch()
        
        # assign second file to token
        demo_scene = self.db.Scene(game=game)
        url = game.get_image_url(id2)
        self.db.Token(scene=demo_scene, url=url, posx=200, posy=150, size=20)
        self.db.commit()
        
        # expect 1st and 3rd file to be abandoned
        # @NOTE: 2nd is assigned, 4th is the last (keeps next id consistent)
        abandoned = game.get_abandoned_images()
        self.assertIn(str(p1), abandoned)
        self.assertNotIn(str(p2), abandoned)
        self.assertIn(str(p3), abandoned)
        self.assertNotIn(str(p4), abandoned)

    @db_session
    def test_getBrokenTokens(self):
        game = self.db.Game(url='foo', gm_url='url456')
        game.post_setup()
        
        # create empty file (to mimic uploaded image)
        img_path = self.engine.paths.get_game_path(game.gm_url, game.url)
        id1 = game.get_next_id()
        p1 = img_path / '{0}.png'.format(id1)
        p1.touch()
        
        # create tokens with and without valid image
        demo_scene = self.db.Scene(game=game)
        url = game.get_image_url(id1)
        fine = self.db.Token(scene=demo_scene, url=url, posx=200, posy=150, size=20)
        broken = self.db.Token(scene=demo_scene, url='bullshit.png', posx=200, posy=150, size=20)
        static = self.db.Token(scene=demo_scene, url='/static/paths/are/fine.png', posx=200, posy=150, size=20)
        self.db.commit()
        
        # expect broken token to be identified
        all_broken = game.get_broken_tokens()
        self.assertEqual(len(all_broken), 1)
        self.assertIn(broken, all_broken)
        self.assertNotIn(fine, all_broken)
        self.assertNotIn(static, all_broken)

    @db_session
    def test_removeMusic(self):
        game = self.db.Game(url='foo', gm_url='url456')
        game.post_setup()
        
        # expect music to be deleted on cleanup
        img_path = self.engine.paths.get_game_path(game.gm_url, game.url)
        p3 = img_path / '3.mp3'
        p3.touch()
        game.remove_music()
        self.assertFalse(os.path.exists(p3))
    
    @db_session
    def test_cleanup(self):
        game = self.db.Game(url='foo', gm_url='url456')
        game.post_setup()
        
        # create three empty files (to mimic uploaded images)
        img_path = self.engine.paths.get_game_path(game.gm_url, game.url)
        id1 = game.get_next_id()
        p1 = img_path / '{0}.png'.format(id1)
        with open(p1, 'w') as h:  # write different content because of hashing
            h.write('FOOBAR')
        id2 = game.get_next_id()
        p2 = img_path / '{0}.png'.format(id2)
        with open(p2, 'w') as h:  # write different content because of hashing
            h.write('AAB')
        p2.touch()   
        id3 = game.get_next_id()
        p3 = img_path / '{0}.png'.format(id3)
        with open(p3, 'w') as h:  # write different content because of hashing
            h.write('AB234')
        p3.touch()
        
        game.make_md5s()

        for i in range(120):
            self.db.Roll(game=game, name='foo', color='red', sides=4, result=3)
            self.db.Roll(game=game, name='foo', color='red', sides=4, result=3, timeid=15)
            self.db.Roll(game=game, name='foo', color='red', sides=4, result=3, timeid=15)

        # expect images to be hashed
        with open(p1, 'rb') as h:
            md5_1 = self.engine.get_md5(h)
        with open(p2, 'rb') as h:
            md5_2 = self.engine.get_md5(h)
        with open(p3, 'rb') as h:
            md5_3 = self.engine.get_md5(h)
        self.assertEqual(game.get_id_by_md5(md5_1), id1)
        self.assertEqual(game.get_id_by_md5(md5_2), id2)
        self.assertEqual(game.get_id_by_md5(md5_3), id3)
        
        # assign second file to token
        demo_scene = self.db.Scene(game=game)
        url = game.get_image_url(id2)
        self.db.Token(scene=demo_scene, url=url, posx=200, posy=150, size=20)
        self.db.commit()
        
        # expect outdated rolls to be deleted
        now = self.engine.latest_rolls + 1
        b, r, t, m = game.cleanup(now)
        self.assertEqual(r, 120)
        rolls_left = self.db.Roll.select(game=game)
        self.assertEqual(len(rolls_left), 240)
        
        # expect unused files to be deleted
        self.assertEqual(b, 6)
        self.assertFalse(os.path.exists(p1))
        self.assertTrue(os.path.exists(p2))

        self.assertEqual(game.get_id_by_md5(md5_1), None)
        self.assertEqual(game.get_id_by_md5(md5_2), id2)

        # expect music to still be present
        p3 = img_path / '4.mp3'    
        p3.touch()
        game.cleanup(now)
        self.assertTrue(os.path.exists(p3))
        
    @db_session
    def test_preDelete(self):
        game = self.db.Game(url='foo', gm_url='url456')
        game.post_setup()
        
        # create an empty file (to make sure it isn't blocking removing the directory)
        img_path = self.engine.paths.get_game_path(game.gm_url, game.url)
        id1 = game.get_next_id()
        p1 = img_path / '{0}.png'.format(id1)
        p1.touch()
        url = game.get_image_url(id1)
        
        # create two demo scenes with tokens
        scene1 = self.db.Scene(game=game)
        for i in range(7):
            self.db.Token(scene=scene1, url=url, posx=200, posy=150, size=20)
        scene2 = self.db.Scene(game=game)
        for i in range(4):
            self.db.Token(scene=scene2, url=url, posx=200, posy=150, size=20)
        self.db.commit()
        
        # prepare game for deletion
        game.pre_delete()
        self.assertFalse(os.path.exists(img_path))
        gm_cache = self.engine.cache.get_from_url('url456')
        game_cache = gm_cache.get(game)
        self.assertEqual(game_cache, None)
        
        # delete game
        game.delete()
        self.db.commit() 

    @db_session
    def test_toDict(self):
        game = self.db.Game(url='foo', gm_url='url456')
        game.post_setup()
        
        # create two demo scenes with tokens
        url = game.get_image_url('123')
        scene1 = self.db.Scene(game=game)
        self.db.Token(scene=scene1, url=url, posx=0, posy=0, size=-1)  # background
        for i in range(7):
            self.db.Token(scene=scene1, url=url, posx=200, posy=150, size=20)
        scene2 = self.db.Scene(game=game)
        for i in range(4):
            self.db.Token(scene=scene2, url=url, posx=200, posy=150, size=20)
        self.db.commit()

        # create a timer token
        self.db.Token(scene=scene1, url='/url456/foo/token_d20.png', posx=100, posy=5, size=40)

        # build dict from game, scenes and tokens
        data = game.to_dict()

        # check all token data in each scene
        for scene in data["scenes"]:
            for i in scene["tokens"]:
                token = data["tokens"][i]
                # test keys
                self.assertIn('url', token)
                self.assertIn('posx', token)
                self.assertIn('posy', token)
                self.assertIn('zorder', token)
                self.assertIn('size', token)
                self.assertIn('rotate', token)
                self.assertIn('flipx', token)
                self.assertIn('locked', token)
                self.assertIn('text', token)
                self.assertIn('color', token)
                # test values
                # note: urls are mostly int (regular tokens) but can be str (timer)
                self.assertIsInstance(token['posx'], int)
                self.assertIsInstance(token['posy'], int)
                self.assertIsInstance(token['zorder'], int)
                self.assertIsInstance(token['size'], int)
                self.assertIsInstance(token['rotate'], float)
                self.assertIsInstance(token['flipx'], bool)
                self.assertIsInstance(token['locked'], bool)
                self.assertIsInstance(token['text'], str)
                self.assertIsInstance(token['color'], str)
            # check scene background
            background_id = scene["backing"]
            if background_id is not None:
                self.assertIn(background_id, scene["tokens"])
        
    @db_session
    def test_toZip(self):
        game = self.db.Game(url='foo', gm_url='url456')
        game.post_setup()
        
        # create an empty file (to make sure it isn't blocking removing the directory)
        img_path = self.engine.paths.get_game_path(game.gm_url, game.url)
        id1 = game.get_next_id()
        p1 = img_path / '{0}.png'.format(id1)
        p1.touch()
        url = game.get_image_url(id1)

        # create dummy music
        p2 = img_path / '0.mp3'    
        p2.touch()

        # create two demo scenes with tokens
        scene1 = self.db.Scene(game=game)
        self.db.Token(scene=scene1, url=url, posx=0, posy=0, size=-1)  # background
        for i in range(7):
            self.db.Token(scene=scene1, url=url, posx=200, posy=150, size=20)
        scene2 = self.db.Scene(game=game)
        for i in range(4):
            self.db.Token(scene=scene2, url=url, posx=200, posy=150, size=20)
        self.db.commit()

        # create a timer token
        self.db.Token(scene=scene1, url='/url456/foo/token_d20.png', posx=100, posy=5, size=40)
        
        # create zip file
        fname, path = game.to_zip()
        zip_path = path / fname
        
        # expect music to still be present
        self.assertTrue(os.path.exists(p2))
        
        # unzip to temp dir to test zip integrity
        with tempfile.TemporaryDirectory() as tmp_dir:
            with zipfile.ZipFile(zip_path, 'r') as fp:
                fp.extractall(tmp_dir)
            
            # load json
            json_path = os.path.join(tmp_dir, 'game.json')
            self.assertTrue(os.path.exists(json_path))
            with open(json_path, 'r') as h:
                data = json.load(h)
            
            # check all images being numbered and with PNG- or MP3-extension
            for fname in os.listdir(tmp_dir):
                if fname == 'game.json':
                    continue
                parts = fname.split('.')
                self.assertEqual(len(parts), 2)
                int(parts[0])
                self.assertIn(parts[1], ['png', 'mp3'])
            
            # check all token data in each scene
            for scene in data["scenes"]:
                for i in scene["tokens"]:
                    token = data["tokens"][i]
                    # test keys
                    self.assertIn('url', token)
                    self.assertIn('posx', token)
                    self.assertIn('posy', token)
                    self.assertIn('zorder', token)
                    self.assertIn('size', token)
                    self.assertIn('rotate', token)
                    self.assertIn('flipx', token)
                    self.assertIn('locked', token)
                    # test values
                    # note: urls are mostly int (regular tokens) but can be str (timer)
                    self.assertIsInstance(token['posx'], int)
                    self.assertIsInstance(token['posy'], int)
                    self.assertIsInstance(token['zorder'], int)
                    self.assertIsInstance(token['size'], int)
                    self.assertIsInstance(token['rotate'], float)
                    self.assertIsInstance(token['flipx'], bool)
                    self.assertIsInstance(token['locked'], bool)
                    # test image existence
                    if isinstance(token['posx'], str):
                        # don't test whether static image exists
                        continue
                    img_path = pathlib.Path(tmp_dir) / '{0}.png'.format(token['url'])
                    self.assertTrue(os.path.exists(img_path))
                # check scene background
                background_id = scene["backing"]
                if background_id is not None:
                    self.assertIn(background_id, scene["tokens"])
        
    @db_session
    def test_fromImage(self):
        pil_img = Image.new(mode='RGB', size=(32, 32))
        with tempfile.NamedTemporaryFile('wb') as wh:
            pil_img.save(wh.name, 'PNG')
            with open(wh.name, 'rb') as rh:
                # prepare fileupload
                fupload = FileUpload(rh, 'test.png', 'test.png')
                
                game = self.db.Game.from_image(
                    gm=self.engine.main_db.GM.select(lambda g: g.url == 'url456').first(),
                    url='bar',
                    handle=fupload
                )
                
                # expect proper scenes' order
                self.assertEqual(len(game.order), 1)
                
                # assert one scene with only one token, which the background
                self.assertEqual(len(game.scenes), 1)
                scene = list(game.scenes)[0]
                tokens = self.db.Token.select(lambda t: t.scene == scene)
                self.assertEqual(len(tokens), 1)
                self.assertEqual(tokens.first().size, -1)
                
                # assert token's image exist
                img_path = self.engine.paths.get_game_path(game.gm_url, game.url)
                img_id = tokens.first().url.split('/')[-1]
                img_fname = img_path / img_id
                self.assertTrue(os.path.exists(img_fname))
    
    @db_session
    def test_fromDict(self):
        game = self.db.Game(url='foo', gm_url='url456')
        game.post_setup()
        
        # create an empty file (to make sure it isn't blocking removing the directory)
        img_path = self.engine.paths.get_game_path(game.gm_url, game.url)
        id1 = game.get_next_id()
        p1 = img_path / '{0}.png'.format(id1)
        p1.touch()
        url = game.get_image_url(id1)
        
        # create two demo scenes with tokens
        scene1 = self.db.Scene(game=game)
        self.db.Token(scene=scene1, url=url, posx=0, posy=0, size=-1)  # background
        for i in range(7):
            self.db.Token(scene=scene1, url=url, posx=200, posy=150, size=20)
        scene2 = self.db.Scene(game=game)
        for i in range(4):
            self.db.Token(scene=scene2, url=url, posx=123, posy=456, size=78, text='foo', color='#00FF00')
        self.db.commit()
        
        # create dict
        data = game.to_dict()

        # create copy of original game by loading dict
        game2 = self.db.Game(url='bar', gm_url='url456')
        game2.post_setup()
        self.db.commit()
        game2.from_dict(data)
        self.db.commit()
        
        # expect proper scenes' order
        self.assertEqual(len(game2.order), 2)
        
        # assert both games having the same scenes
        self.assertEqual(len(game2.scenes), len(game.scenes))
        game2_scene1 = list(game2.scenes)[0]
        game2_scene2 = list(game2.scenes)[1]
        query1 = self.db.Token.select(lambda _t: _t.scene == game2_scene1)
        query2 = self.db.Token.select(lambda _t: _t.scene == game2_scene2)
        # order isn't important here
        if len(query1) == 4:
            query1, query2 = query2, query1
        # test data
        self.assertEqual(len(query1), 8)
        self.assertEqual(len(query2), 4)
        for t in query1:
            if t.posx == 0:
                # background
                self.assertEqual(t.url, url.replace('foo', 'bar'))
                self.assertEqual(t.posy, 0)
                self.assertEqual(t.size, -1)
            else:
                # tokens
                self.assertEqual(t.url, url.replace('foo', 'bar'))
                self.assertEqual(t.posx, 200)
                self.assertEqual(t.posy, 150)
                self.assertEqual(t.size, 20)
        for t in query2:
            self.assertEqual(t.url, url.replace('foo', 'bar'))
            self.assertEqual(t.posx, 123)
            self.assertEqual(t.posy, 456)
            self.assertEqual(t.size, 78)
            self.assertEqual(t.text, 'foo')
            self.assertEqual(t.color, '#00FF00')

        # fromDict is backwards compatible
        for raw in data['tokens']:
            del raw['rotate']
            del raw['flipx']
            del raw['locked']
            del raw['text']
            del raw['color']
        # create another copy of that game
        game3 = self.db.Game(url='bar2', gm_url='url456')
        game3.post_setup()
        self.db.commit()
        game3.from_dict(data)
        self.db.commit() 
        
    @db_session
    def test_fromZip(self):
        game = self.db.Game(url='foo', gm_url='url456')
        game.post_setup()
        
        # create an empty file (to make sure it isn't blocking removing the directory)
        img_path = self.engine.paths.get_game_path(game.gm_url, game.url)
        id1 = game.get_next_id()
        p1 = img_path / '{0}.png'.format(id1)
        p1.touch()
        url = game.get_image_url(id1)
        
        # create two demo scenes with tokens
        scene1 = self.db.Scene(game=game)
        self.db.Token(scene=scene1, url=url, posx=0, posy=0, size=-1)  # background
        for i in range(7):
            self.db.Token(scene=scene1, url=url, posx=200, posy=150, size=20)
        scene2 = self.db.Scene(game=game)
        for i in range(4):
            self.db.Token(scene=scene2, url=url, posx=200, posy=150, size=20)
        self.db.commit()
        
        # create zip file
        fname, path = game.to_zip()
        zip_path = path / fname
        
        # create copy of original game by importing zip
        with open(zip_path, 'rb') as fp:
            fupload = FileUpload(fp, 'demo.zip', 'demo.zip')
            
            game2 = self.db.Game.from_zip(
                gm=self.engine.main_db.GM.select(lambda g: g.url == 'url456').first(),
                url='bar',
                handle=fupload
            )
            
            # expect proper scenes' order
            self.assertEqual(len(game2.order), 2)
            
            # assert both games having the same scenes
            self.assertEqual(len(game2.scenes), len(game.scenes))
            game2_scene1 = list(game2.scenes)[0]
            game2_scene2 = list(game2.scenes)[1]
            query1 = self.db.Token.select(lambda _t: _t.scene == game2_scene1)
            query2 = self.db.Token.select(lambda _t: _t.scene == game2_scene2)
            # order isn't important here
            self.assertEqual({4, 8}, {len(query1), len(query2)})
            
            # assert all images being there
            new_img_path = self.engine.paths.get_game_path(game2.gm_url, game2.url)
            for t in query1:
                img_id = t.url.split('/')[-1]
                img_fname = new_img_path / img_id
                self.assertTrue(os.path.exists(img_fname))
            for t in query2:
                img_id = t.url.split('/')[-1]
                img_fname = new_img_path / img_id
                self.assertTrue(os.path.exists(img_fname))
            
            # @NOTE: exact token data (position etc.) isn't tested here
        
        # create corrupt json file inside zip
        with tempfile.TemporaryDirectory() as tmp_dir:
            # manipulate json
            json_path = os.path.join(tmp_dir, 'game.json')
            with open(json_path, 'w') as h:
                h.write('{some[brokenstuff": "(}]')
            
            # pack zip (without any images)
            with zipfile.ZipFile(zip_path, "w") as h:
                h.write(json_path, 'game.json')

        # try to upload that corrupted file
        with open(zip_path, 'rb') as fp:
            fupload = FileUpload(fp, 'demo.zip', 'demo.zip')
            
            game3 = self.db.Game.from_zip(
                gm=self.engine.main_db.GM.select(lambda g: g.url == 'url456').first(),
                url='bar',
                handle=fupload
            )
            self.assertIsNone(game3) 
