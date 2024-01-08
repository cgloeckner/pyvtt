"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

from bottle import *


def register(engine: any):

    @get('/vtt/thumbnail/<gm_url>/<game_url>/<scene_id:int>')
    def get_scene_thumbnail(gm_url: str, game_url: str, scene_id: int):
        # load GM from cache
        gm_cache = engine.cache.get_from_url(gm_url)
        if gm_cache is None:
            # @NOTE: not logged because somebody may play around with this
            abort(404)

        # load scene from GM's database
        scene = gm_cache.db.Scene.select(lambda scn: scn.id == scene_id and scn.game.url == game_url).first()
        if scene is None:
            # @NOTE: not logged because somebody may play around with this
            abort(404)

        engine.paths.get_game_path(gm_url, game_url)
        if scene.backing is not None:
            game_url = scene.backing.url
        else:
            game_url = '/static/empty.jpg'

        redirect(game_url)

    @get('/vtt/thumbnail/<gm_url>/<game_url>')
    def get_game_thumbnail(gm_url: str, game_url: str):
        # load GM from cache
        gm_cache = engine.cache.get_from_url(gm_url)
        if gm_cache is None:
            # @NOTE: not logged because somebody may play around with this
            abort(404)

        # load game from GM's database
        game = gm_cache.db.Game.select(lambda g: g.url == game_url).first()
        if game is None:
            # @NOTE: not logged because somebody may play around with this
            abort(404)

        redirect(f'/vtt/thumbnail/{gm_url}/{game_url}/{game.active}')
