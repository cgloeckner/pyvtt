"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

import json
import random

from bottle import *


def register(engine):

    @get('/vtt/thumbnail/<gmurl>/<url>/<scene_id:int>')
    def get_scene_thumbnail(gmurl, url, scene_id):
        # load GM from cache
        gm_cache = engine.cache.getFromUrl(gmurl)
        if gm_cache is None:
            # @NOTE: not logged because somebody may play around with this
            abort(404)

        # load scene from GM's database
        scene = gm_cache.db.Scene.select(lambda s: s.id == scene_id and s.game.url == url).first()
        if scene is None:
            # @NOTE: not logged because somebody may play around with this
            abort(404)

        engine.paths.get_game_path(gmurl, url)
        if scene.backing != None:
            url = scene.backing.url
        else:
            url = '/static/empty.jpg'

        redirect(url)

    @get('/vtt/thumbnail/<gmurl>/<url>')
    def get_game_thumbnail(gmurl, url):
        # load GM from cache
        gm_cache = engine.cache.getFromUrl(gmurl)
        if gm_cache is None:
            # @NOTE: not logged because somebody may play around with this
            abort(404)

        # load game from GM's database
        game = gm_cache.db.Game.select(lambda g: g.url == url).first()
        if game is None:
            # @NOTE: not logged because somebody may play around with this
            abort(404)

        redirect('/vtt/thumbnail/{0}/{1}/{2}'.format(gmurl, url, game.active))
