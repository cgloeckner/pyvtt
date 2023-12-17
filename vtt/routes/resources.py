"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

from bottle import *


def register(engine: any):

    @get('/static/<filename>')
    def static_files(filename: str):
        root = engine.paths.get_static_path()
        if not os.path.isdir(root) or not os.path.exists(root / filename):
            root = './static'

        # @NOTE: no need to check file extension, this directory is
        # meant to be accessible as a whole

        return static_file(filename, root=root)

    @get('/static/assets/<filename>')
    def static_assets(filename: str):
        root = engine.paths.get_assets_path()
        if not os.path.isdir(root) or not os.path.exists(root / filename):
            # use default root
            root = engine.paths.get_assets_path(default=True)
        return static_file(filename, root=root)

    @get('/static/client/<filename>')
    def static_client_code(filename: str):
        root = engine.paths.get_client_code_path()
        if not os.path.isdir(root) or not os.path.exists(root / filename):
            # use default root
            root = engine.paths.get_static_path(default=True) / 'client'

        return static_file(filename, root=root)

    @get('/asset/<gm_url>/<game_url>/<filename>')
    def game_asset(gm_url: str, game_url: str, filename: str):
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

        # only allow specific file types
        if not filename.endswith('.png') and not filename.endswith('.mp3'):
            abort(404)

        # try to load asset file from disk
        root = engine.paths.get_game_path(gm_url, game_url)
        return static_file(filename, root)
