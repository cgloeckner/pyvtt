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
from PIL import Image

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

        # test scene ordering
        self.assertEqual(game.order, list())

    @db_session
    def test_reorderScenes(self):
        game = self.db.Game(url='foo', gm_url='url456')
        for i in range(4):
            last_scene = self.db.Scene(game=game)
        self.db.commit()

        # expect no order list yet
        self.assertEqual(game.order, list())

        game.reorderScenes()
        
        # expect ordered by IDs
        last_id = last_scene.id
        self.assertEqual(game.order, [last_id-3, last_id-2, last_id-1, last_id])
    
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

        # create music file (not expected to be picked up)
        p5 = img_path / self.engine.paths.getMusicFileName()
        p5.touch()
        
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
        
        # can upload image file
        pil_img = Image.new(mode='RGB', size=(32, 32))
        with tempfile.NamedTemporaryFile('wb') as wh:
            pil_img.save(wh.name, 'PNG')
            with open(wh.name, 'rb') as rh:
                # prepare fileupload
                fupload = FileUpload(rh, 'test.png', 'test.png')
                
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

        # cannot upload broken file
        with tempfile.NamedTemporaryFile('wb') as wh:
            wh.write(b'0' * 2**20)
            with open(wh.name, 'rb') as rh:
                # prepare fileupload
                fupload = FileUpload(rh, 'test.png', 'test.png')
                
                # test upload result
                old_id = game.getNextId()
                url = game.upload(fupload)
                self.assertIsNone(url)
        
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
    def test_getBrokenTokens(self):
        game = self.db.Game(url='foo', gm_url='url456')
        game.postSetup()
        
        # create empty file (to mimic uploaded image)
        img_path = self.engine.paths.getGamePath(game.gm_url, game.url)
        id1 = game.getNextId()
        p1 = img_path / '{0}.png'.format(id1)
        p1.touch()
        
        # create tokens with and without valid image
        demo_scene = self.db.Scene(game=game)
        url = game.getImageUrl(id1)
        fine   = self.db.Token(scene=demo_scene, url=url, posx=200, posy=150, size=20)
        broken = self.db.Token(scene=demo_scene, url='bullshit.png', posx=200, posy=150, size=20)
        self.db.commit()
        
        # expect broken token to be identified
        all_broken = game.getBrokenTokens()
        self.assertEqual(len(all_broken), 1)
        self.assertIn(broken, all_broken)
        self.assertNotIn(fine, all_broken)

    @db_session
    def test_removeMusic(self):
        game = self.db.Game(url='foo', gm_url='url456')
        game.postSetup()
        
        # expect music to be deleted on cleanup
        img_path = self.engine.paths.getGamePath(game.gm_url, game.url)
        p3 = img_path / self.engine.paths.getMusicFileName()
        p3.touch()
        game.removeMusic()
        self.assertFalse(os.path.exists(p3))
    
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

        for i in range(120):
            self.db.Roll(game=game, name='foo', color='red', sides=4, result=3)
            self.db.Roll(game=game, name='foo', color='red', sides=4, result=3, timeid=15)
        
        # assoign second file to token
        demo_scene = self.db.Scene(game=game)
        url = game.getImageUrl(id2)
        self.db.Token(scene=demo_scene, url=url, posx=200, posy=150, size=20)
        self.db.commit()
        
        # expect outdated rolls to be deleted
        now = self.engine.latest_rolls + 1
        game.cleanup(now)
        rolls_left = self.db.Roll.select(game=game)
        self.assertEqual(len(rolls_left), 120)
        
        # expect unused files to be deleted
        game.cleanup(now)
        self.assertFalse(os.path.exists(p1))
        self.assertTrue(os.path.exists(p2))

        # expect music to be deleted on cleanup
        p3 = img_path / self.engine.paths.getMusicFileName()
        p3.touch()
        game.cleanup(now)
        self.assertFalse(os.path.exists(p3))
        
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
    def test_toDict(self):
        game = self.db.Game(url='foo', gm_url='url456')
        game.postSetup()
        
        # create two demo scenes with tokens
        url = game.getImageUrl('123')
        scene1 = self.db.Scene(game=game)
        self.db.Token(scene=scene1, url=url, posx=0, posy=0, size=-1) # background
        for i in range(7):
            self.db.Token(scene=scene1, url=url, posx=200, posy=150, size=20)
        scene2 = self.db.Scene(game=game)
        for i in range(4):
            self.db.Token(scene=scene2, url=url, posx=200, posy=150, size=20)
        self.db.commit()

        # build dict from game, scenes and tokens
        data = game.toDict()

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
                self.assertIsInstance(token['url'], int)
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
        pil_img = Image.new(mode='RGB', size=(32, 32))
        with tempfile.NamedTemporaryFile('wb') as wh:
            pil_img.save(wh.name, 'PNG')
            with open(wh.name, 'rb') as rh:
                # prepare fileupload
                fupload = FileUpload(rh, 'test.png', 'test.png')
                
                game = self.db.Game.fromImage(
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
                img_path = self.engine.paths.getGamePath(game.gm_url, game.url)
                img_id = tokens.first().url.split('/')[-1]
                img_fname = img_path / img_id
                self.assertTrue(os.path.exists(img_fname))
    
    @db_session
    def test_fromDict(self):
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
            self.db.Token(scene=scene2, url=url, posx=123, posy=456, size=78, text='foo', color='#00FF00')
        self.db.commit()
        
        # create dict
        data = game.toDict()

        # create copy of original game by loading dict
        game2 = self.db.Game(url='bar', gm_url='url456')
        game2.postSetup()
        self.db.commit()
        game2.fromDict(data)
        self.db.commit()
        
        # expect proper scenes' order
        self.assertEqual(len(game2.order), 2)
        
        # assert both games having the same scenes
        self.assertEqual(len(game2.scenes), len(game.scenes))
        game2_scene1 = list(game2.scenes)[0]
        game2_scene2 = list(game2.scenes)[1]
        query1 = self.db.Token.select(lambda t: t.scene == game2_scene1)
        query2 = self.db.Token.select(lambda t: t.scene == game2_scene2)
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
        game3.postSetup()
        self.db.commit()
        game3.fromDict(data)
        self.db.commit() 
        
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
            
            # expect proper scenes' order
            self.assertEqual(len(game2.order), 2)
            
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
            
            # @NOTE: exact token data (position etc.) isn't tested here
        
        # create corrupt json file inside zip
        with tempfile.TemporaryDirectory() as tmp_dir:
            # manipulate json
            json_path = os.path.join(tmp_dir, 'game.json')
            with open(json_path , 'w') as h:
                h.write('{some[brokenstuff": "(}]')
            
            # pack zip (without any images)
            with zipfile.ZipFile(zip_path, "w") as h:
                h.write(json_path, 'game.json')

        # try to upload that corrupted file
        with open(zip_path, 'rb') as fp:
            fupload = FileUpload(fp, 'demo.zip', 'demo.zip')
            
            game3 = self.db.Game.fromZip(
                gm=self.engine.main_db.GM.select(lambda g: g.url == 'url456').first(),
                url='bar',
                handle=fupload
            )
            self.assertIsNone(game3) 

