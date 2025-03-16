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
import io

import bottle
from PIL import Image, UnidentifiedImageError
from pony.orm import *

from .gm import BaseGm


CleanupReport = tuple[int, int, int, int]


def register(engine: any, db: Database):

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

        def post_setup(self):
            """ Adds the game's directory and prepare the md5 cache."""
            engine.storage.init_game(self.gm_url, self.url)
 
            # add to the engine's cache
            gm_cache = engine.cache.get_from_url(self.gm_url)
            gm_cache.insert(self)

            # NOTE that order == None if database was freshly migrated
            # since order is optional, but should be provided
            self.order = list()

        def reorder_scenes(self):
            """ Reorder scenes based on their IDs. """
            self.order = [s.id for s in self.scenes]
            self.order.sort()
 
        def get_image_url(self, image_id: int) -> str:
            return f'/asset/{self.gm_url}/{self.url}/{image_id}.png'

        def upload(self, handle: bottle.FileUpload) -> str | None:
            """Upload image into storage return the url to the image."""
            img_id = engine.storage.upload_image(self.gm_url, self.url, handle)
            if img_id is None:
                return None

            return self.get_image_url(img_id)

        @staticmethod
        def get_id_from_url(url: str) -> id:
            return int(url.split('/')[-1].split('.')[0])

        def get_abandoned_images(self) -> list[str]:
            """Return a list of all image ids that are not used in any scene in this game"""
            # check all existing images
            all_images = engine.storage.get_all_images(self.gm_url, self.url)

            abandoned = list()
            last_id = engine.storage.get_max_id(all_images)
            for filename in all_images:
                image_id = engine.storage.id_from_filename(filename)
                if image_id == last_id:
                    # keep this image to avoid next id to cause
                    # unexpected browser cache behavior
                    continue

                # check for any tokens
                image_url = self.get_image_url(image_id)
                token = db.Token.select(lambda t: t.url == image_url).first()
                if token is None:
                    # found abandoned image
                    abandoned.append(image_id)

            return abandoned

        def get_broken_tokens(self) -> list[db.Entity]:
            # query all images
            all_images = engine.storage.get_all_images(self.gm_url, self.url)

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
            """Remove all music"""
            engine.storage.remove_music(self.gm_url, self.url, range(engine.file_limit['num_music']))

        def cleanup(self, now) -> CleanupReport:
            """ Cleanup game's unused image and token data. """
            # delete all abandoned images
            relevant = self.get_abandoned_images()
            num_bytes = engine.storage.remove_images(self.gm_url, self.url, relevant, id_query=self.get_id_from_url)
            num_md5s = len(relevant)

            # delete all outdated rolls
            rolls = db.Roll.select(lambda r: r.game == self and r.timeid < now - engine.latest_rolls)
            num_rolls = len(rolls)
            rolls.delete()

            # query and remove all tokens that have no image
            relevant = self.get_broken_tokens()
            num_tokens = len(relevant)
            for t in relevant:
                t.delete()

            return num_bytes, num_rolls, num_tokens, num_md5s

        def pre_delete(self) -> int:
            """ Remove this game from disk before removing it from
            the GM's database. """
            engine.logging.info('|--x Removing {0}'.format(self.url))

            num_bytes = engine.storage.remove_game(self.gm_url, self.url)

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

            # create zip file in memory
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # add game.json
                game_json = json.dumps(data, indent=4)
                zip_file.writestr('game.json', game_json)
                for filename in engine.storage.get_all_images(self.gm_url, self.url):
                    # load image from storage
                    image_id = engine.storage.id_from_filename(filename)
                    local_path = engine.storage.get_local_image_path(self.gm_url, self.url, image_id)
                    with open(local_path, 'rb') as handle:
                        # add image
                        img_binary = handle.read()
                        zip_file.writestr(filename, img_binary)

            # save zip to file
            zip_path = engine.paths.get_export_path()
            zip_file = '{0}_{1}.zip'.format(self.gm_url, self.url)

            with open(zip_path / zip_file, 'wb') as handle:
                handle.write(zip_buffer.getvalue())

            # build zip file
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
