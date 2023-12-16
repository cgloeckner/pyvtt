"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

import json
import os
import shutil
import tempfile
import time
import zipfile

from PIL import Image, UnidentifiedImageError
from pony.orm import *


def register(engine, db):

    class Game(db.Entity):
        id = PrimaryKey(int, auto=True)
        url = Required(str, unique=True)  # since each GM has its own games database
        scenes = Set("Scene", cascade_delete=True)  # forward deletion to scenes
        timeid = Required(float, default=0.0)  # used for cleanup
        active = Optional(int)
        rolls = Set("Roll")
        gm_url = Required(str)  # used for internal things
        order = Optional(IntArray)  # scene ordering by their ids

        def hasExpired(self, now, scale=1.0):
            delta = now - self.timeid
            return self.timeid > 0 and delta > engine.cleanup['expire'] * scale

        def mayExpireSoon(self, now):
            return self.hasExpired(now, scale=0.5)

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

            # check if image exists for all md5s
            for md5 in data.copy():
                fname = '{0}.png'.format(data[md5])
                if not os.path.exists(root / fname):
                    del data[md5]

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

            with engine.locks[self.gm_url]:  # make IO access safe
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
            root = engine.paths.getGamePath(self.gm_url, self.url)
            return [f for f in os.listdir(root) if f.endswith('.png')]

        def getNextId(self):
            """Note: needs to be called from a threadsafe context."""
            max_id = 0
            fnames = self.getAllImages()
            split = lambda s: int(s.split('.png')[0])
            if len(fnames) > 0:
                last_png = max(fnames, key=split)
                max_id = split(last_png) + 1
            return max_id

        def getImageUrl(self, image_id):
            return '/asset/{0}/{1}/{2}.png'.format(self.gm_url, self.url, image_id)

        def getFileSize(self, url):
            game_root = engine.paths.getGamePath(self.gm_url, self.url)
            img_fname = url.split('/')[-1]
            local_path = os.path.join(game_root, img_fname)
            return os.path.getsize(local_path)

        def upload(self, handle):
            """Save the given image via file handle and return the url to the image.
            """
            suffix = '.{0}'.format(handle.filename.split(".")[-1])
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
                image_id = self.getNextId()
                local_path = game_root / '{0}.png'.format(image_id)
                with engine.locks[self.gm_url]:  # make IO access safe
                    if new_md5 not in engine.checksums[self.getUrl()]:
                        # copy image to target
                        shutil.copyfile(tmpfile.name, local_path)

                        # store pair: checksum => image_id
                        engine.checksums[self.getUrl()][new_md5] = image_id

                # fetch remote path (query image_id via by checksum)
                remote_path = self.getImageUrl(engine.checksums[self.getUrl()][new_md5])

                # assure image file exists
                img_id = int(remote_path.split('/')[-1].split('.png')[0])
                local_path = game_root / '{0}.png'.format(img_id)
                with engine.locks[self.gm_url]:  # make IO access safe
                    if not os.path.exists(local_path):
                        # copy image to target
                        shutil.copyfile(tmpfile.name, local_path)

                        engine.logging.warning('Image got re-uploaded to fix a cache error')
                        if engine.notify_api is not None:
                            engine.notify_api(remote_path,
                                              'Image got re-uploaded to fix a cache error:\n {0}'.format(remote_path))

                return remote_path

        @staticmethod
        def getIdFromUrl(url):
            return int(url.split('/')[-1].split('.')[0])

        def getAbandonedImages(self):
            # check all existing images
            game_root = engine.paths.getGamePath(self.gm_url, self.url)
            all_images = list()
            with engine.locks[self.gm_url]:  # make IO access safe
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
            with engine.locks[self.gm_url]:  # make IO access safe
                all_images = self.getAllImages()

            # query all tokens without valid image
            broken = list()
            for s in self.scenes:
                for t in s.tokens:
                    if t.url.split('/')[-1] in all_images:
                        continue
                    if not t.url.startswith('/static'):  # e.g. timer token
                        broken.append(t)
            return broken

        def removeMusic(self):
            """ Remove music. """
            root = engine.paths.getGamePath(self.gm_url, self.url)
            with engine.locks[self.gm_url]:  # make IO access safe
                for n in range(engine.file_limit['num_music']):
                    fname = root / '{0}.mp3'.format(n)
                    if os.path.exists(fname):
                        os.remove(fname)

        def cleanup(self, now):
            """ Cleanup game's unused image and token data. """
            num_bytes = 0
            num_rolls = 0
            num_tokens = 0

            # query and remove all images that are not used as tokens
            relevant = self.getAbandonedImages()
            with engine.locks[self.gm_url]:  # make IO access safe
                for fname in relevant:
                    num_bytes += os.path.getsize(fname)
                    os.remove(fname)
                    # remove image's md5 hash from cache
                    self.removeMd5(self.getIdFromUrl(fname))

            # delete all outdated rolls
            rolls = db.Roll.select(lambda r: r.game == self and r.timeid < now - engine.latest_rolls)
            num_rolls = len(rolls)
            rolls.delete()

            # query and remove all tokens that have no image
            relevant = self.getBrokenTokens()
            num_tokens = len(relevant)
            for t in relevant:
                t.delete()

            num_md5s = self.makeMd5s()

            return num_bytes, num_rolls, num_tokens, num_md5s

        def preDelete(self):
            """ Remove this game from disk before removing it from
            the GM's database. """
            engine.logging.info('|--x Removing {0}'.format(self.url))

            # remove game directory (including all images)
            game_path = engine.paths.getGamePath(self.gm_url, self.url)
            num_bytes = os.path.getsize(game_path)

            with engine.locks[self.gm_url]:  # make IO access safe
                shutil.rmtree(game_path)

            # remove game from GM's cache
            gm_cache = engine.cache.getFromUrl(self.gm_url)
            gm_cache.remove(self)

            # remove all scenes
            for s in self.scenes:
                s.preDelete()
                s.delete()

            return num_bytes

        def toDict(self):
            # collect all tokens in this game
            tokens = list()
            id_translation = dict()  # required because the current token ids will not persist
            game_tokens = db.Token.select(
                lambda t: t.scene is not None
                          and t.scene.game is not None
                          and t.scene.game == self
            )
            for t in game_tokens:
                url = t.url.split('/')[-1].split('.png')[0]
                if url.isdigit():
                    url = int(url)

                tokens.append({
                    "url": url,
                    "posx": t.posx,
                    "posy": t.posy,
                    "zorder": t.zorder,
                    "size": t.size,
                    "rotate": t.rotate,
                    "flipx": t.flipx,
                    "locked": t.locked,
                    "text": t.text,
                    "color": t.color
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
                    "tokens": tkns,
                    "backing": backing_file
                })
                if self.active == s.id:
                    active = len(scenes) - 1

            return {
                "tokens": tokens,
                "scenes": scenes
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
                    tmp.seek(0)  # rewind!
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
                    if isinstance(url, int):
                        # regular token
                        newurl = self.getImageUrl(url)
                    else:
                        # timer token
                        newurl = '/static/assets/{0}.png'.format(url)
                    # create token
                    t = db.Token(
                        scene=scene,
                        url=newurl,
                        posx=token_data['posx'],
                        posy=token_data['posy'],
                        zorder=token_data.get('zorder', 0),
                        size=token_data['size'],
                        rotate=token_data.get('rotate', 0.0),
                        flipx=token_data.get('flipx', False),
                        locked=token_data.get('locked', False),
                        text=token_data.get('text', ''),
                        color=token_data.get('color', '')
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
                    with open(json_path, 'r') as h:
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

    return Game
