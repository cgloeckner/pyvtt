#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import os, pathlib, time, uuid, tempfile, shutil, zipfile, json, math

from gevent import lock
from PIL import Image, UnidentifiedImageError

from pony.orm import *


__author__ = 'Christian Glöckner'
__licence__ = 'MIT'


# NOTE: screen is exactly 16:9
MAX_SCENE_WIDTH  = 1008
MAX_SCENE_HEIGHT = 567

MIN_TOKEN_SIZE   = 1
MAX_TOKEN_SIZE   = 1000

def createGmDatabase(engine, filename):
    """ Creates a new database for with GM entities such as Tokens,
    Scenes etc.
    """
    db = Database()

    class Token(db.Entity):
        id      = PrimaryKey(int, auto=True)
        scene   = Required("Scene")
        url     = Required(str)
        posx    = Required(int)
        posy    = Required(int)
        zorder  = Required(int, default=0)
        size    = Required(int)
        rotate  = Required(float, default=0.0)
        flipx   = Required(bool, default=False)
        locked  = Required(bool, default=False)
        timeid  = Required(float, default=0.0) # dirty flag
        back    = Optional("Scene") # link to same scene as above but may be None
        text    = Optional(str) # text
        color   = Optional(str) # used for label
        
        def update(self, timeid, pos=None, zorder=None, size=None, rotate=None, flipx=None, locked=None, label=None):
            """Handle update of several data fields. The timeid is set if anything
            has actually changed.
            """
            if self.locked and locked is None:
                # token is locked and not unlocked
                return
            
            if locked is not None and self.locked != locked:
                self.timeid = timeid
                self.locked = locked
            
            if pos != None:
                # force position onto scene (canvas)
                self.posx = min(MAX_SCENE_WIDTH, max(0, pos[0]))
                self.posy = min(MAX_SCENE_HEIGHT, max(0, pos[1]))
                self.timeid = timeid
            
            if zorder != None:
                self.zorder = zorder
                self.timeid = timeid
            
            if size != None:
                self.size = min(MAX_TOKEN_SIZE, max(MIN_TOKEN_SIZE, size))
                self.timeid = timeid
                
            if rotate != None:
                self.rotate = rotate
                self.timeid = timeid
        
            if flipx != None:
                self.flipx  = flipx
                self.timeid = timeid

            if label != None:
                self.text   = label[0][:15]
                self.color  = label[1]
                self.timeid = timeid
        
        @staticmethod
        def getPosByDegree(origin, k, n):
            """ Get Position in circle around origin of the k-th item of n. """
            # determine degree and radius
            degree = k * 360 / n
            radius = 32 * n ** 0.5
            if n == 1:
                radius = 0
            
            # calculate position in unit circle
            s = math.sin(degree * 3.14 / 180)
            c = math.cos(degree * 3.14 / 180) 
            
            # calculate actual position
            x = int(origin[0] - radius * s)
            y = int(origin[1] + radius * c)
            
            # force position onto scene (canvas)
            x = min(MAX_SCENE_WIDTH, max(0, x))
            y = min(MAX_SCENE_HEIGHT, max(0, y))
            
            return (x, y)


    # -----------------------------------------------------------------------------

    class Scene(db.Entity):
        id      = PrimaryKey(int, auto=True)
        game    = Required("Game")
        tokens  = Set("Token", cascade_delete=True, reverse="scene") # forward deletion to tokens
        backing = Optional("Token", reverse="back") # background token
        
        def preDelete(self):
            # delete all tokens
            for t in self.tokens:
                t.delete()
            self.backing = None

    # -----------------------------------------------------------------------------

    class Roll(db.Entity):
        id     = PrimaryKey(int, auto=True)
        game   = Required("Game")
        name   = Required(str)
        color  = Required(str)
        sides  = Required(int)
        result = Required(int)
        timeid = Required(float, default=0.0)

    # -----------------------------------------------------------------------------

    class Game(db.Entity):
        id     = PrimaryKey(int, auto=True)
        url    = Required(str, unique=True) # since each GM has its own games database
        scenes = Set("Scene", cascade_delete=True) # forward deletion to scenes
        timeid = Required(float, default=0.0) # used for cleanup
        active = Optional(int)
        rolls  = Set(Roll)
        gm_url = Required(str) # used for internal things
        order  = Optional(IntArray) # scene ordering by their ids
        
        def getUrl(self):
            return '{0}/{1}'.format(self.gm_url, self.url)
        
        def makeMd5s(self):                 
            md5_path = engine.paths.getMd5Path(self.gm_url, self.url)
            root = engine.paths.getGamePath(self.gm_url, self.url)
            all_images = self.getAllImages()
            
            # load md5 hashes from json-file
            data = dict()
            if os.path.exists(md5_path):
                with open(md5_path, 'r') as handle:
                    data = json.load(handle)
            
            # check for images without md5
            missing = list()
            for fname in all_images:
                fname_id = int(fname.split('.')[0])
                if fname_id not in data.values():
                    missing.append(fname)

            # create missing md5s
            for fname in missing:
                # create md5 of file (assumed to be images)
                with open(root / fname, "rb") as handle:
                    md5 = engine.getMd5(handle)
                    data[md5] = int(fname.split('.')[0])
            engine.checksums[self.getUrl()] = data

            # save md5 hashes to json-file
            with open(md5_path, 'w') as handle:
                json.dump(data, handle)

            return len(missing)

        def getIdByMd5(self, md5):
            return engine.checksums[self.getUrl()].get(md5, None) 

        def removeMd5(self, img_id):
            cache = engine.checksums[self.getUrl()]
            # linear search for image hash
            for k, v in cache.items():
                if v == img_id:
                    del cache[k]
                    return

        def postSetup(self):
            """ Adds the game's directory and prepare the md5 cache.
            """
            img_path = engine.paths.getGamePath(self.gm_url, self.url)
            
            with engine.locks[self.gm_url]: # make IO access safe
                if not os.path.isdir(img_path):
                    os.mkdir(img_path)
            
            # add to the engine's cache
            gm_cache = engine.cache.getFromUrl(self.gm_url)
            gm_cache.insert(self)

            # NOTE that order == None if database was freshly migrated
            # since order is optional, but should be provided
            self.order = list()
            
            self.makeMd5s()

        def reorderScenes(self):
            """ Reorder scenes based on their IDs. """
            self.order = [s.id for s in self.scenes]
            self.order.sort()
        
        def getAllImages(self):
            """Note: needs to be called from a threadsafe context."""
            root   = engine.paths.getGamePath(self.gm_url, self.url)
            return [f for f in os.listdir(root) if f.endswith('.png')]
        
        def getNextId(self):
            """Note: needs to be called from a threadsafe context."""
            max_id = 0
            fnames = self.getAllImages()
            split = lambda s: int(s.split('.png')[0])
            if len(fnames) > 0:
                last_png = max(fnames, key=split)
                max_id   = split(last_png) + 1
            return max_id

        def getImageUrl(self, image_id):
            return '/token/{0}/{1}/{2}.png'.format(self.gm_url, self.url, image_id)

        def getFileSize(self, url):
            game_root  = engine.paths.getGamePath(self.gm_url, self.url)
            img_fname  = url.split('/')[-1]
            local_path = os.path.join(game_root, img_fname)
            return os.path.getsize(local_path)

        def upload(self, handle):
            """Save the given image via file handle and return the url to the image.
            """
            suffix  = '.{0}'.format(handle.filename.split(".")[-1])
            with tempfile.NamedTemporaryFile(suffix=suffix) as tmpfile:
                # save image to tempfile
                handle.save(tmpfile.name, overwrite=True)

                # check file format
                try:
                    Image.open(tmpfile.name)
                except UnidentifiedImageError:
                    # unsupported file format
                    return None
                
                # create md5 checksum for duplication test
                new_md5 = engine.getMd5(tmpfile.file)
                
                game_root = engine.paths.getGamePath(self.gm_url, self.url)
                with engine.locks[self.gm_url]: # make IO access safe
                    if new_md5 not in engine.checksums[self.getUrl()]:
                        # copy image to target
                        image_id   = self.getNextId()
                        local_path = game_root / '{0}.png'.format(image_id)
                        shutil.copyfile(tmpfile.name, local_path)
                        
                        # store pair: checksum => image_id
                        engine.checksums[self.getUrl()][new_md5] = image_id
                
                # propagate remote path (query image_id by checksum)
                return self.getImageUrl(engine.checksums[self.getUrl()][new_md5])
        
        @staticmethod
        def getIdFromUrl(url):
            return int(url.split('/')[-1].split('.')[0])
        
        def getAbandonedImages(self):
            # check all existing images
            game_root = engine.paths.getGamePath(self.gm_url, self.url)
            all_images = list()
            with engine.locks[self.gm_url]: # make IO access safe
                all_images = self.getAllImages()
            
            abandoned = list()
            last_id = self.getNextId() - 1
            for image_id in all_images:
                this_id = int(image_id.split('.')[0])
                if this_id == last_id:
                    # keep this image to avoid next id to cause
                    # unexpected browser cache behavior
                    continue
                # create url (ignore png-extension due to os.listdir)
                url = self.getImageUrl(this_id)
                # check for any tokens
                t = db.Token.select(lambda t: t.url == url).first()
                if t is None:
                    # found abandoned image
                    abandoned.append(os.path.join(game_root, image_id))
                
            return abandoned

        def getBrokenTokens(self):
            # query all images
            all_images = list()
            with engine.locks[self.gm_url]: # make IO access safe
                all_images = self.getAllImages()

            # query all tokens without valid image
            broken = list()
            for s in self.scenes:
                for t in s.tokens:
                    if t.url.split('/')[-1] not in all_images:
                        broken.append(t)
            return broken

        def removeMusic(self):
            """ Remove music. """
            root = engine.paths.getGamePath(self.gm_url, self.url)
            with engine.locks[self.gm_url]: # make IO access safe
                for n in range(engine.file_limit['num_music']):
                    fname = root / '{0}.mp3'.format(n)
                    if os.path.exists(fname):
                        os.remove(fname)
        
        def cleanup(self, now):
            """ Cleanup game's unused image and token data. """   
            engine.logging.info('|--> Cleaning {0}'.format(self.url))
            
            # query and remove all images that are not used as tokens
            relevant = self.getAbandonedImages()
            with engine.locks[self.gm_url]: # make IO access safe
                for fname in relevant:
                    engine.logging.info('     |--x Removing {0}'.format(fname))
                    os.remove(fname)
                    # remove image's md5 hash from cache
                    self.removeMd5(self.getIdFromUrl(fname))

            # delete all outdated rolls
            rolls = db.Roll.select(lambda r: r.game == self and r.timeid < now - engine.latest_rolls)
            if len(rolls) > 0:
                engine.logging.info('     |--> {0} outdated rolls'.format(len(rolls)))
            rolls.delete()

            # query and remove all tokens that have no image
            relevant = self.getBrokenTokens()
            for t in relevant:
                t.delete()
            
        def preDelete(self):
            """ Remove this game from disk before removing it from
            the GM's database. """
            engine.logging.info('|--x Removing {0}'.format(self.url))
            
            # remove game directory (including all images)
            game_path = engine.paths.getGamePath(self.gm_url, self.url)
            with engine.locks[self.gm_url]: # make IO access safe
                shutil.rmtree(game_path)
            
            # remove game from GM's cache
            gm_cache = engine.cache.getFromUrl(self.gm_url)
            gm_cache.remove(self)
            
            # remove all scenes
            for s in self.scenes:
                s.preDelete()
                s.delete()

        def toDict(self):
            # collect all tokens in this game
            tokens = list()
            id_translation = dict() # required because the current token ids will not persist
            game_tokens = db.Token.select(
                lambda t: t.scene is not None
                    and t.scene.game is not None 
                    and t.scene.game == self
            )
            for t in game_tokens:
                tokens.append({
                    "url"    : int(t.url.split('/')[-1].split('.png')[0]), # only take image id
                    "posx"   : t.posx,
                    "posy"   : t.posy,
                    "zorder" : t.zorder,
                    "size"   : t.size,
                    "rotate" : t.rotate,
                    "flipx"  : t.flipx,
                    "locked" : t.locked,
                    "text"   : t.text,
                    "color"  : t.color
                })
                id_translation[t.id] = len(tokens) - 1
            
            # collect all scenes in this game
            scenes = list()
            active = 0
            for s in self.scenes.order_by(lambda s: s.id):
                tkns = list()
                for t in s.tokens:
                    # query new id from translation dict
                    tkns.append(id_translation[t.id])
                backing_file = None
                if s.backing is not None:
                    backing_file = id_translation[s.backing.id]
                scenes.append({
                    "tokens"  : tkns,
                    "backing" : backing_file
                })
                if self.active == s.id:
                    active = len(scenes) - 1
            
            return {
                "tokens" : tokens,
                "scenes" : scenes
            }
            
        def toZip(self):
            # remove abandoned images
            self.cleanup(time.time())
            
            data = self.toDict()
            
            # build zip file
            zip_path = engine.paths.getExportPath()
            zip_file = '{0}_{1}.zip'.format(self.gm_url, self.url)
            
            with zipfile.ZipFile(zip_path / zip_file, "w") as h:
                # create temporary file and add it to the zip
                with tempfile.NamedTemporaryFile() as tmp:
                    s = json.dumps(data, indent=4)
                    tmp.write(s.encode('utf-8'))
                    tmp.seek(0) # rewind!
                    h.write(tmp.name, 'game.json')
                
                # add images to the zip, too
                p = engine.paths.getGamePath(self.gm_url, self.url)
                for img in self.getAllImages():
                    h.write(p / img, img)
            
            return zip_file, zip_path
        
        @staticmethod
        def fromImage(gm, url, handle):
            # create game with that image as background
            game = db.Game(url=url, gm_url=gm.url)
            try:
                game.postSetup()
            except KeyError:
                # url already in use
                return None
            
            # create initial scene
            scene = db.Scene(game=game)
            db.commit()
            game.active = scene.id
            
            # set image as background
            token_url = game.upload(handle)
            if token_url is None:
                # rollback
                game.delete()
                return None
            
            t = db.Token(scene=scene, timeid=0, url=token_url, posx=0, posy=0, size=-1)
            db.commit()
            
            scene.backing = t
            db.commit()
            
            # setup scenes' order (for initial scene)
            game.reorderScenes()
            
            return game

        def fromDict(self, data):
            # create scenes
            for sid, s in enumerate(data["scenes"]):
                scene = db.Scene(game=self)
                
                # create tokens for that scene
                for token_id in s["tokens"]:
                    token_data = data["tokens"][token_id]
                    url = token_data['url']
                    if isinstance(url, str): # backwards compatibility
                        url = url.split('.png')[0]
                    t = db.Token(                                
                        scene=scene, url=self.getImageUrl(url),
                        posx   = token_data['posx'],
                        posy   = token_data['posy'],
                        zorder = token_data.get('zorder', 0),
                        size   = token_data['size'],
                        rotate = token_data.get('rotate', 0.0),
                        flipx  = token_data.get('flipx', False),
                        locked = token_data.get('locked', False),
                        text   = token_data.get('text', ''),
                        color  = token_data.get('color', '')
                    )
                    if s["backing"] == token_id:
                        db.commit()
                        scene.backing = t
                    
                if self.active is None:
                    # select first scene as active
                    self.active = scene.id

            db.commit()
            # setup scenes' order (for initial scene)
            self.reorderScenes()

        @staticmethod
        def fromZip(gm, url, handle):
            # unzip uploaded file to temp dir
            with tempfile.TemporaryDirectory() as tmp_dir:
                zip_path = os.path.join(tmp_dir, handle.filename)
                handle.save(str(zip_path))
                try:
                    with zipfile.ZipFile(zip_path, 'r') as fp:
                        fp.extractall(tmp_dir)
                except zipfile.BadZipFile:
                    # zip is corrupted
                    return None

                # create all game data
                data = dict()
                json_path = os.path.join(tmp_dir, 'game.json')
                if not os.path.exists(json_path):
                    return None
                try:
                    with open(json_path , 'r') as h:
                        data = json.load(h)
                except json.decoder.JSONDecodeError:
                    # json is corrupted
                    return None
                
                # create game
                game = db.Game(url=url, gm_url=gm.url)
                try:
                    game.postSetup()
                except KeyError:
                    # url already in use
                    return None
                db.commit()
                
                # copy images to game directory
                img_path = engine.paths.getGamePath(gm.url, url)
                for fname in os.listdir(tmp_dir):
                    if fname.endswith('.png'):
                        src_path = os.path.join(tmp_dir, fname)
                        dst_path = img_path / fname
                        shutil.copyfile(src_path, dst_path)
                
                # create scenes
                try:
                    game.fromDict(data)
                except KeyError as e:
                    # delete game
                    game.delete()
                    return None
                    
                db.commit()
            
                return game
     
    # -----------------------------------------------------------------------------
    
    db.bind('sqlite', filename, create_db=True)
    db.generate_mapping(create_tables=True)
    
    return db


def createMainDatabase(engine):
    """ Creates main database for GM data.
    """
    
    db = Database()
    
    class GM(db.Entity):
        id        = PrimaryKey(int, auto=True)
        name      = Required(str)
        url       = Required(str, unique=True)
        sid       = Required(str, unique=True)
        timeid    = Optional(float) # used for cleanup
        
        def makeLock(self):
            engine.locks[self.url] = lock.RLock();
        
        def postSetup(self):
            self.timeid = int(time.time())
            
            self.makeLock()
            
            root_path = engine.paths.getGmsPath(self.url)
            
            with engine.locks[self.url]: # make IO access safe
                if not os.path.isdir(root_path):
                    os.mkdir(root_path)
            
            # add to engine's GM cache
            engine.cache.insert(self)

        def cleanup(self, gm_db, now):
            """ Cleanup GM's games' outdated rolls, unused images or
            event remove expired games (see engine.expire). """
            engine.logging.info('Cleaning GM {0} <{1}>'.format(self.name, self.url))

            for g in gm_db.Game.select():
                if g.timeid > 0 and g.timeid + engine.expire < now:
                    # remove this game
                    g.preDelete()
                    g.delete()
                    
                else:
                    # cleanup this game
                    g.cleanup(now)
            
        def preDelete(self):
            """ Remove this GM from disk to allow removing him from
            the main database.
            """  
            engine.logging.info('Removing GM {0} <{1}>'.format(self.name, self.url))
            
            # remove GM's directory (including his database, all games and images)
            root_path = engine.paths.getGmsPath(self.url)
            
            with engine.locks[self.url]: # make IO access safe
                shutil.rmtree(root_path)
            
            # remove GM from engine's cache
            engine.cache.remove(self)
            
        def refreshSession(self, response):
            """ Refresh session id. """
            now = time.time()
            self.timeid = now
            response.set_cookie('session', self.sid, path='/', expires=now + engine.expire)
            
        @staticmethod
        def loadFromSession(request):
            """ Fetch GM from session id and ip address. """
            sid = request.get_cookie('session')
            return db.GM.select(lambda g: g.sid == sid).first()
        
        @staticmethod
        def genSession():
            return uuid.uuid4().hex
        
    # -----------------------------------------------------------------
    
    db.bind('sqlite', str(engine.paths.getMainDatabasePath()), create_db=True)
    db.generate_mapping(create_tables=True)
    
    return db

