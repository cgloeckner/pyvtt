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
import pathlib
import typing

import bottle
from PIL import Image, UnidentifiedImageError
from pony.orm import *

from .gm import BaseGm


CleanupReport = tuple[int, int, int, int]


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

        def has_expired(self, now: int, scale: float = 1.0) -> bool:
            delta = now - self.timeid
            return self.timeid > 0 and delta > engine.cleanup['expire'] * scale

        def may_expire_soon(self, now: int) -> bool:
            return self.has_expired(now, scale=0.5)

        def get_url(self) -> str:
            return f'{self.gm_url}/{self.url}'

        def make_md5s(self) -> int:
            md5_path = engine.paths.get_md5_path(self.gm_url, self.url)
            root = engine.paths.get_game_path(self.gm_url, self.url)
            all_images = self.get_all_images()

            # load md5 hashes from json-file
            data = dict()
            if os.path.exists(md5_path):
                with open(md5_path, 'r') as handle:
                    data = json.load(handle)

            # check if image exists for all md5 hashes
            for md5 in data.copy():
                filename = '{0}.png'.format(data[md5])
                if not os.path.exists(root / filename):
                    del data[md5]

            # check for images without md5
            missing = list()
            for filename in all_images:
                filename_id = int(filename.split('.')[0])
                if filename_id not in data.values():
                    missing.append(filename)

            # create missing md5 hashes
            for filename in missing:
                # create md5 of file (assumed to be images)
                with open(root / filename, "rb") as handle:
                    md5 = engine.get_md5(handle)
                    data[md5] = int(filename.split('.')[0])
            engine.checksums[self.get_url()] = data

            # save md5 hashes to json-file
            with open(md5_path, 'w') as handle:
                json.dump(data, handle)

            return len(missing)

        def get_id_by_md5(self, md5: str) -> int | None:
            return engine.checksums[self.get_url()].get(md5, None)

        def remove_md5(self, img_id: int):
            cache = engine.checksums[self.get_url()]
            # linear search for image hash
            for k, v in cache.items():
                if v == img_id:
                    del cache[k]
                    return

        def post_setup(self):
            """ Adds the game's directory and prepare the md5 cache."""
            img_path = engine.paths.get_game_path(self.gm_url, self.url)

            with engine.locks[self.gm_url]:  # make IO access safe
                if not os.path.isdir(img_path):
                    os.mkdir(img_path)

            # add to the engine's cache
            gm_cache = engine.cache.get_from_url(self.gm_url)
            gm_cache.insert(self)

            # NOTE that order == None if database was freshly migrated
            # since order is optional, but should be provided
            self.order = list()

            self.make_md5s()

        def reorder_scenes(self):
            """ Reorder scenes based on their IDs. """
            self.order = [s.id for s in self.scenes]
            self.order.sort()

        def get_all_images(self) -> list[str]:
            """Note: needs to be called from a threadsafe context."""
            root = engine.paths.get_game_path(self.gm_url, self.url)
            return [f for f in os.listdir(root) if f.endswith('.png')]

        def get_next_id(self) -> int:
            """Note: needs to be called from a threadsafe context."""
            max_id = 0
            filenames = self.get_all_images()

            def split(s: str) -> int:
                return int(s.split('.png')[0])

            if len(filenames) > 0:
                last_png = max(filenames, key=split)
                max_id = split(last_png) + 1
            return max_id

        def get_image_url(self, image_id: int) -> str:
            return f'/asset/{self.gm_url}/{self.url}/{image_id}.png'

        def get_file_size(self, url: str) -> int:
            game_root = engine.paths.get_game_path(self.gm_url, self.url)
            img_filename = url.split('/')[-1]
            local_path = os.path.join(game_root, img_filename)
            return os.path.getsize(local_path)

        def upload(self, handle: bottle.FileUpload) -> str | None:
            """Save the given image via file handle and return the url to the image."""
            suffix = '.{0}'.format(handle.filename.split(".")[-1])
            with tempfile.NamedTemporaryFile(suffix=suffix) as tmp_file:
                # save image to temporary file
                handle.save(tmp_file.name, overwrite=True)

                # check file format
                try:
                    Image.open(tmp_file.name)
                except UnidentifiedImageError:
                    # unsupported file format
                    return None

                # create md5 checksum for duplication test
                new_md5 = engine.get_md5(tmp_file.file)

                game_root = engine.paths.get_game_path(self.gm_url, self.url)
                image_id = self.get_next_id()
                local_path = game_root / f'{image_id}.png'
                with engine.locks[self.gm_url]:  # make IO access safe
                    if new_md5 not in engine.checksums[self.get_url()]:
                        # copy image to target
                        shutil.copyfile(tmp_file.name, local_path)

                        # store pair: checksum => image_id
                        engine.checksums[self.get_url()][new_md5] = image_id

                # fetch remote path (query image_id via by checksum)
                remote_path = self.get_image_url(engine.checksums[self.get_url()][new_md5])

                # assure image file exists
                img_id = int(remote_path.split('/')[-1].split('.png')[0])
                local_path = game_root / f'{img_id}.png'
                with engine.locks[self.gm_url]:  # make IO access safe
                    if not os.path.exists(local_path):
                        # copy image to target
                        shutil.copyfile(tmp_file.name, local_path)

                        engine.logging.warning('Image got re-uploaded to fix a cache error')
                        if engine.notify_api is not None:
                            engine.notify_api(remote_path,
                                              f'Image got re-uploaded to fix a cache error:\n {remote_path}')

                return remote_path

        @staticmethod
        def get_id_from_url(url: str) -> id:
            return int(url.split('/')[-1].split('.')[0])

        def get_abandoned_images(self) -> list[str]:
            # check all existing images
            game_root = engine.paths.get_game_path(self.gm_url, self.url)
            with engine.locks[self.gm_url]:  # make IO access safe
                all_images = self.get_all_images()

            abandoned = list()
            last_id = self.get_next_id() - 1
            for image_id in all_images:
                this_id = int(image_id.split('.')[0])
                if this_id == last_id:
                    # keep this image to avoid next id to cause
                    # unexpected browser cache behavior
                    continue
                # create url (ignore png-extension due to os.listdir)
                url = self.get_image_url(this_id)
                # check for any tokens
                token = db.Token.select(lambda t: t.url == url).first()
                if token is None:
                    # found abandoned image
                    abandoned.append(os.path.join(game_root, image_id))

            return abandoned

        def get_broken_tokens(self) -> list[db.Entity]:
            # query all images
            with engine.locks[self.gm_url]:  # make IO access safe
                all_images = self.get_all_images()

            # query all tokens without valid image
            broken = list()
            for s in self.scenes:
                for t in s.tokens:
                    if t.url.split('/')[-1] in all_images:
                        continue
                    if not t.url.startswith('/static'):  # e.g. timer token
                        broken.append(t)
            return broken

        def remove_music(self):
            """ Remove music. """
            root = engine.paths.get_game_path(self.gm_url, self.url)
            with engine.locks[self.gm_url]:  # make IO access safe
                for n in range(engine.file_limit['num_music']):
                    fname = root / '{0}.mp3'.format(n)
                    if os.path.exists(fname):
                        os.remove(fname)

        def cleanup(self, now) -> CleanupReport:
            """ Cleanup game's unused image and token data. """
            num_bytes = 0

            # query and remove all images that are not used as tokens
            relevant = self.get_abandoned_images()
            with engine.locks[self.gm_url]:  # make IO access safe
                for filename in relevant:
                    num_bytes += os.path.getsize(filename)
                    os.remove(filename)
                    # remove image's md5 hash from cache
                    self.remove_md5(self.get_id_from_url(filename))

            # delete all outdated rolls
            rolls = db.Roll.select(lambda r: r.game == self and r.timeid < now - engine.latest_rolls)
            num_rolls = len(rolls)
            rolls.delete()

            # query and remove all tokens that have no image
            relevant = self.get_broken_tokens()
            num_tokens = len(relevant)
            for t in relevant:
                t.delete()

            num_md5s = self.make_md5s()

            return num_bytes, num_rolls, num_tokens, num_md5s

        def pre_delete(self) -> int:
            """ Remove this game from disk before removing it from
            the GM's database. """
            engine.logging.info('|--x Removing {0}'.format(self.url))

            # remove game directory (including all images)
            game_path = engine.paths.get_game_path(self.gm_url, self.url)
            num_bytes = os.path.getsize(game_path)

            with engine.locks[self.gm_url]:  # make IO access safe
                shutil.rmtree(game_path)

            # remove game from GM's cache
            gm_cache = engine.cache.get_from_url(self.gm_url)
            gm_cache.remove(self)

            # remove all scenes
            for s in self.scenes:
                s.pre_delete()
                s.delete()

            return num_bytes

        def to_dict(self) -> dict[str, list[db.Entity]]:
            # collect all tokens in this game
            tokens = list()
            id_translation = dict()  # required because the current token ids will not persist
            game_tokens = db.Token.select(
                lambda t: t.scene is not None and t.scene.game is not None and t.scene.game == self
            )
            for token in game_tokens:
                url = token.url.split('/')[-1].split('.png')[0]
                if url.isdigit():
                    url = int(url)

                tokens.append({
                    "url": url,
                    "posx": token.posx,
                    "posy": token.posy,
                    "zorder": token.zorder,
                    "size": token.size,
                    "rotate": token.rotate,
                    "flipx": token.flipx,
                    "locked": token.locked,
                    "text": token.text,
                    "color": token.color
                })
                id_translation[token.id] = len(tokens) - 1

            # collect all scenes in this game
            scenes = list()
            for scene in self.scenes.order_by(lambda s: s.id):
                tkns = list()
                for token in scene.tokens:
                    # query new id from translation dict
                    tkns.append(id_translation[token.id])
                backing_file = None
                if scene.backing is not None:
                    backing_file = id_translation[scene.backing.id]
                scenes.append({
                    "tokens": tkns,
                    "backing": backing_file
                })

            return {
                "tokens": tokens,
                "scenes": scenes
            }

        def to_zip(self) -> tuple[str, pathlib.Path]:
            # remove abandoned images
            self.cleanup(time.time())

            data = self.to_dict()

            # build zip file
            zip_path = engine.paths.get_export_path()
            zip_file = '{0}_{1}.zip'.format(self.gm_url, self.url)

            with zipfile.ZipFile(zip_path / zip_file, "w") as h:
                # create temporary file and add it to the zip
                with tempfile.NamedTemporaryFile() as tmp:
                    s = json.dumps(data, indent=4)
                    tmp.write(s.encode('utf-8'))
                    tmp.seek(0)  # rewind!
                    h.write(tmp.name, 'game.json')

                # add images to the zip, too
                p = engine.paths.get_game_path(self.gm_url, self.url)
                for img in self.get_all_images():
                    h.write(p / img, img)

            return zip_file, zip_path

        @classmethod
        def from_image(cls, gm: BaseGm, url: str, handle: bottle.FileUpload) -> typing.Self | None:
            # create game with that image as background
            game = db.Game(url=url, gm_url=gm.url)
            try:
                game.post_setup()
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
            game.reorder_scenes()

            return game

        def from_dict(self, data: dict[str, db.Entity]) -> None:
            # create scenes
            for sid, s in enumerate(data["scenes"]):
                scene = db.Scene(game=self)

                # create tokens for that scene
                for token_id in s["tokens"]:
                    token_data = data["tokens"][token_id]
                    url = token_data['url']
                    if isinstance(url, int):
                        # regular token
                        new_url = self.get_image_url(url)
                    else:
                        # timer token
                        new_url = '/static/assets/{0}.png'.format(url)
                    # create token
                    t = db.Token(
                        scene=scene,
                        url=new_url,
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
            self.reorder_scenes()

        @classmethod
        def from_zip(cls, gm: BaseGm, url: str, handle: bottle.FileUpload) -> typing.Self | None:
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
                    game.post_setup()
                except KeyError:
                    # url already in use
                    return None
                db.commit()

                # copy images to game directory
                img_path = engine.paths.get_game_path(gm.url, url)
                for filename in os.listdir(tmp_dir):
                    if filename.endswith('.png'):
                        src_path = os.path.join(tmp_dir, filename)
                        dst_path = img_path / filename
                        shutil.copyfile(src_path, dst_path)

                # create scenes
                try:
                    game.from_dict(data)
                except KeyError as _:
                    # delete game
                    game.delete()
                    return None

                db.commit()

                return game

    return Game
