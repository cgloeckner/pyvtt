#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import os, pathlib, tempfile, zipfile, json

from bottle import FileUpload
from pony.orm import db_session

import orm

from test.utils import EngineBaseTest

class GameTest(EngineBaseTest):
    
    def setUp(self):
        super().setUp()
        
        # finish GM data
        with db_session:
            gm = self.engine.main_db.GM(name='user123', url='url456', sid='123456')
            gm.postSetup()
        
        # create GM database
        self.db = orm.createGmDatabase(engine=self.engine, filename=':memory:')
        
    def tearDown(self):
        del self.db
        
    @db_session
    def test_getUrl(self):
        game = self.db.Game(url='foo', gm_url='url456')
        url  = game.getUrl()
        self.assertEqual(url, 'url456/foo')
        
    @db_session
    def test_makeMd5s(self):
        game = self.db.Game(url='foo', gm_url='url456')
        game.postSetup()
        
        # create empty files (to mimic uploaded images)
        img_path = self.engine.paths.getGamePath(game.gm_url, game.url)
        id1 = game.getNextId()
        p1 = img_path / '{0}.png'.format(id1)
        p1.touch()
        id2 = game.getNextId()
        p2 = img_path / '{0}.png'.format(id2)
        with open(p2, 'w') as h: # write different content because of hashing
            h.write('2')
        id3 = game.getNextId()
        p3 = img_path / '{0}.png'.format(id3)
        with open(p3, 'w') as h: # write different content because of hashing
            h.write('3')
        id4 = game.getNextId()
        p4 = img_path / '{0}.png'.format(id4)
        with open(p4, 'w') as h: # write different content because of hashing
            h.write('4')
        
        # assume empty cache
        cache_instance = self.engine.checksums[game.getUrl()]
        self.assertEqual(len(cache_instance), 0)
        
        game.makeMd5s()
        
        # test image IDs in cache
        cache_instance = self.engine.checksums[game.getUrl()]
        self.assertEqual(len(cache_instance), 4)
        ids = set()
        for md5 in cache_instance:
            img_id = cache_instance[md5]
            ids.add(img_id)
        self.assertEqual(ids, {0, 1, 2, 3}) # compare sets
        
    @db_session
    def test_postSetup(self):
        game = self.db.Game(url='foo', gm_url='url456')
        
        game_path = self.engine.paths.getGamePath(gm=game.gm_url, game=game.url)
        
        # test game setup
        self.assertFalse(os.path.isdir(game_path))
        game.postSetup()
        self.assertTrue(os.path.isdir(game_path))
        
    @db_session
    def test_getAllImages(self):
        game = self.db.Game(url='foo', gm_url='url456')
        game.postSetup()
        
        # create empty files (to mimic uploaded images)
        img_path = self.engine.paths.getGamePath(game.gm_url, game.url)
        id1 = game.getNextId()
        p1 = img_path / '{0}.png'.format(id1)
        p1.touch()
        id2 = game.getNextId()
        p2 = img_path / '{0}.png'.format(id2)
        p2.touch()
        id3 = game.getNextId()
        p3 = img_path / '{0}.png'.format(id3)
        p3.touch()
        id4 = game.getNextId()
        p4 = img_path / '{0}.png'.format(id4)
        p4.touch()
        
        # test files being detected
        files = set(game.getAllImages())
        self.assertEqual(files, {'0.png', '1.png', '2.png', '3.png'})
        
    @db_session
    def test_getNextId(self):
        game = self.db.Game(url='foo', gm_url='url456')
        game.postSetup()
        
        # starting id
        i = game.getNextId()
        self.assertEqual(i, 0)
        
        i = game.getNextId()
        self.assertEqual(i, 0)
        
        # gaps ignored for next_id
        img_path = self.engine.paths.getGamePath(game.gm_url, game.url)
        for i in [0, 1, 2, 3, 4, 6, 7, 8, 10, 11, 12]:
            p = img_path / '{0}.png'.format(i)
            p.touch()
        i = game.getNextId()
        self.assertEqual(i, 13)
        
        # first unused id
        p = img_path / '5.png'
        p.touch()     
        i = game.getNextId()
        self.assertEqual(i, 13)
        
    @db_session
    def test_getImageUrl(self):
        game = self.db.Game(url='foo', gm_url='url456')
        game.postSetup()
        
        url = game.getImageUrl(17)
        self.assertEqual(url, '/token/url456/foo/17.png')
        
    @db_session
    def test_getFileSize(self):
        game = self.db.Game(url='foo', gm_url='url456')
        game.postSetup()
        
        # create empty files (to mimic uploaded images)
        img_path = self.engine.paths.getGamePath(game.gm_url, game.url)
        id1 = game.getNextId()
        p1 = img_path / '{0}.png'.format(id1)
        p1.touch()
        id2 = game.getNextId()
        p2 = img_path / '{0}.png'.format(id2)
        with open(p2, 'w') as h:
            h.write('test')
        id3 = game.getNextId()
        p3 = img_path / '{0}.png'.format(id3)
        with open(p3, 'w') as h:
            h.write('xy')
        id4 = game.getNextId()
        p4 = img_path / '{0}.png'.format(id4)
        with open(p4, 'w') as h:
            h.write('abc')
        
        # test file sizes
        size1 = game.getFileSize(str(p1))
        size2 = game.getFileSize(str(p2))
        size3 = game.getFileSize(str(p3)) 
        size4 = game.getFileSize(str(p4))
        self.assertEqual(size1, 0)
        self.assertEqual(size2, 4)
        self.assertEqual(size3, 2)
        self.assertEqual(size4, 3)
        
    @db_session
    def test_upload(self):
        game = self.db.Game(url='foo', gm_url='url456')
        game.postSetup()
        
        # prepare FileUpload (with this file for demoing purpose)
        fupload = FileUpload(open(__file__, 'rb'), 'test.png', 'test.png')
        
        # test upload result
        old_id = game.getNextId()
        url = game.upload(fupload)
        new_id = game.getNextId()
        self.assertEqual(old_id + 1, new_id)
        self.assertEqual(url, game.getImageUrl(old_id))
        
        # test file exists   
        img_path = self.engine.paths.getGamePath(game.gm_url, game.url)
        p = img_path / '{0}.png'.format(old_id)
        self.assertTrue(os.path.exists(p))
        
        # check md5 being stored
        md5 = self.engine.getMd5(fupload.file)
        checksums = self.engine.checksums[game.getUrl()]
        self.assertIn(md5, checksums)
        
        # try to reupload file: same file used
        old_id = game.getNextId()
        new_url = game.upload(fupload)
        new_id = game.getNextId()
        self.assertEqual(old_id, new_id)
        self.assertEqual(url, new_url)
        
    def test_getIdFromUrl(self):
        self.assertEqual(self.db.Game.getIdFromUrl('/foo/bar/3.17.png'), 3)
        self.assertEqual(self.db.Game.getIdFromUrl('/0.'), 0)
        with self.assertRaises(ValueError):
            self.db.Game.getIdFromUrl('/a.')
        
    @db_session
    def test_getAbandonedImages(self):
        game = self.db.Game(url='foo', gm_url='url456')
        game.postSetup()
        
        # create empty files (to mimic uploaded images)
        img_path = self.engine.paths.getGamePath(game.gm_url, game.url)
        id1 = game.getNextId()
        p1 = img_path / '{0}.png'.format(id1)
        p1.touch()
        id2 = game.getNextId()
        p2 = img_path / '{0}.png'.format(id2)
        p2.touch()
        id3 = game.getNextId()
        p3 = img_path / '{0}.png'.format(id3)
        p3.touch()
        id4 = game.getNextId()
        p4 = img_path / '{0}.png'.format(id4)
        p4.touch()
        
        # assign second file to token
        demo_scene = self.db.Scene(game=game)
        url = game.getImageUrl(id2)
        self.db.Token(scene=demo_scene, url=url, posx=200, posy=150, size=20)
        self.db.commit()
        
        # expect 1st and 3rd file to be abandoned
        # @NOTE: 2nd is assigned, 4th is the last (keeps next id consistent)
        abandoned = game.getAbandonedImages()
        self.assertIn(str(p1), abandoned)
        self.assertNotIn(str(p2), abandoned)
        self.assertIn(str(p3), abandoned)
        self.assertNotIn(str(p4), abandoned)
        
    @db_session
    def test_cleanup(self):
        game = self.db.Game(url='foo', gm_url='url456')
        game.postSetup()
        
        # create two empty files (to mimic uploaded images)
        img_path = self.engine.paths.getGamePath(game.gm_url, game.url)
        id1 = game.getNextId()
        p1 = img_path / '{0}.png'.format(id1)
        p1.touch()
        id2 = game.getNextId()
        p2 = img_path / '{0}.png'.format(id2)
        p2.touch()
        
        # assoign second file to token
        demo_scene = self.db.Scene(game=game)
        url = game.getImageUrl(id2)
        self.db.Token(scene=demo_scene, url=url, posx=200, posy=150, size=20)
        self.db.commit()
        
        # expect unused files to be deleted
        game.cleanup()                      
        self.assertFalse(os.path.exists(p1))
        self.assertTrue(os.path.exists(p2))
        
    @db_session
    def test_preDelete(self):
        game = self.db.Game(url='foo', gm_url='url456')
        game.postSetup()
        
        # create an empty file (to make sure it isn't blocking removing the directory)
        img_path = self.engine.paths.getGamePath(game.gm_url, game.url)
        id1 = game.getNextId()
        p1 = img_path / '{0}.png'.format(id1)
        p1.touch()
        url = game.getImageUrl(id1)
        
        # create two demo scenes with tokens
        scene1 = self.db.Scene(game=game)
        for i in range(7):
            self.db.Token(scene=scene1, url=url, posx=200, posy=150, size=20)
        scene2 = self.db.Scene(game=game)
        for i in range(4):
            self.db.Token(scene=scene2, url=url, posx=200, posy=150, size=20)
        self.db.commit()
        
        # prepare game for deletion
        game.preDelete()
        self.assertFalse(os.path.exists(img_path))
        gm_cache = self.engine.cache.getFromUrl('url456')
        game_cache = gm_cache.get(game)
        self.assertEqual(game_cache, None)
        
        # delete game
        game.delete()
        self.db.commit() 
        
    @db_session
    def test_toZip(self):
        game = self.db.Game(url='foo', gm_url='url456')
        game.postSetup()
        
        # create an empty file (to make sure it isn't blocking removing the directory)
        img_path = self.engine.paths.getGamePath(game.gm_url, game.url)
        id1 = game.getNextId()
        p1 = img_path / '{0}.png'.format(id1)
        p1.touch()
        url = game.getImageUrl(id1)
        
        # create two demo scenes with tokens
        scene1 = self.db.Scene(game=game)
        self.db.Token(scene=scene1, url=url, posx=0, posy=0, size=-1) # background
        for i in range(7):
            self.db.Token(scene=scene1, url=url, posx=200, posy=150, size=20)
        scene2 = self.db.Scene(game=game)
        for i in range(4):
            self.db.Token(scene=scene2, url=url, posx=200, posy=150, size=20)
        self.db.commit()
        
        # create zip file
        fname, path = game.toZip()
        zip_path    = path / fname
        
        # unzip to temp dir to test zip integrity
        with tempfile.TemporaryDirectory() as tmp_dir:
            with zipfile.ZipFile(zip_path, 'r') as fp:
                fp.extractall(tmp_dir)
            
            # load json
            json_path = os.path.join(tmp_dir, 'game.json')
            self.assertTrue(os.path.exists(json_path))
            with open(json_path, 'r') as h:
                data = json.load(h)
            
            # check all images being numbered and with PNG-extension
            for fname in os.listdir(tmp_dir):
                if fname == 'game.json':
                    continue
                parts = fname.split('.')
                self.assertEqual(len(parts), 2)
                int(parts[0])
                self.assertEqual(parts[1], 'png')
            
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
                    self.assertIsInstance(token['url'], int)
                    self.assertIsInstance(token['posx'], int)
                    self.assertIsInstance(token['posy'], int)
                    self.assertIsInstance(token['zorder'], int)
                    self.assertIsInstance(token['size'], int)
                    self.assertIsInstance(token['rotate'], float)
                    self.assertIsInstance(token['flipx'], bool)
                    self.assertIsInstance(token['locked'], bool)
                    # test image existence
                    img_path = pathlib.Path(tmp_dir) / '{0}.png'.format(token['url'])
                    self.assertTrue(os.path.exists(img_path))
                # check scene background
                background_id = scene["backing"]
                if background_id is not None:
                    self.assertIn(background_id, scene["tokens"])
        
    @db_session
    def test_fromImage(self):
        # create fake fileupload to mimic image
        fupload = FileUpload(open(__file__, 'rb'), 'test.png', __file__)
        
        game = self.db.Game.fromImage(
            gm=self.engine.main_db.GM.select(lambda g: g.url == 'url456').first(),
            url='bar',
            handle=fupload
        )
        
        # assert one scene with only one token, which the background
        self.assertEqual(len(game.scenes), 1)
        scene = list(game.scenes)[0]
        tokens = self.db.Token.select(lambda t: t.scene == scene)
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens.first().size, -1)
        
        # assert token's image exist
        img_path = self.engine.paths.getGamePath(game.gm_url, game.url)
        img_id = tokens.first().url.split('/')[-1]
        img_fname = img_path / img_id
        self.assertTrue(os.path.exists(img_fname))
        
    @db_session
    def test_fromZip(self):
        game = self.db.Game(url='foo', gm_url='url456')
        game.postSetup()
        
        # create an empty file (to make sure it isn't blocking removing the directory)
        img_path = self.engine.paths.getGamePath(game.gm_url, game.url)
        id1 = game.getNextId()
        p1 = img_path / '{0}.png'.format(id1)
        p1.touch()
        url = game.getImageUrl(id1)
        
        # create two demo scenes with tokens
        scene1 = self.db.Scene(game=game)
        self.db.Token(scene=scene1, url=url, posx=0, posy=0, size=-1) # background
        for i in range(7):
            self.db.Token(scene=scene1, url=url, posx=200, posy=150, size=20)
        scene2 = self.db.Scene(game=game)
        for i in range(4):
            self.db.Token(scene=scene2, url=url, posx=200, posy=150, size=20)
        self.db.commit()
        
        # create zip file
        fname, path = game.toZip()
        zip_path    = path / fname
        
        # create copy of original game by importing zip
        with open(zip_path, 'rb') as fp:
            fupload = FileUpload(fp, 'demo.zip', 'demo.zip')
            
            game2 = self.db.Game.fromZip(
                gm=self.engine.main_db.GM.select(lambda g: g.url == 'url456').first(),
                url='bar',
                handle=fupload
            )
            
            # assert both games having the same scenes
            self.assertEqual(len(game2.scenes), len(game.scenes))
            game2_scene1 = list(game2.scenes)[0]
            game2_scene2 = list(game2.scenes)[1]
            query1 = self.db.Token.select(lambda t: t.scene == game2_scene1)
            query2 = self.db.Token.select(lambda t: t.scene == game2_scene2)
            # order isn't important here
            self.assertEqual(set([4, 8]), set([len(query1), len(query2)]))
            
            # assert all images being there
            new_img_path = self.engine.paths.getGamePath(game2.gm_url, game2.url)
            for t in query1:
                img_id = t.url.split('/')[-1]
                img_fname = new_img_path / img_id
                self.assertTrue(os.path.exists(img_fname))
            for t in query2:
                img_id = t.url.split('/')[-1]
                img_fname = new_img_path / img_id
                self.assertTrue(os.path.exists(img_fname))
            
            # @note: exact token data (position etc.) isn't tested here
            
