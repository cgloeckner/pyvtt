"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

from bottle import *


def register(engine):

    @get('/static/<fname>')
    def static_files(fname):
        root = engine.paths.get_static_path()
        if not os.path.isdir(root) or not os.path.exists(root / fname):
            root = './static'

        # @NOTE: no need to check file extension, this directory is
        # meant to be accessable as a whole

        return static_file(fname, root=root)

    @get('/static/assets/<fname>')
    def static_assets(fname):
        root = engine.paths.get_assets_path()
        if not os.path.isdir(root) or not os.path.exists(root / fname):
            # use default root
            root = engine.paths.get_assets_path(default=True)
        return static_file(fname, root=root)

    @get('/static/client/<fname>')
    def static_client_code(fname):
        root = engine.paths.get_client_code_path()
        if not os.path.isdir(root) or not os.path.exists(root / fname):
            # use default root
            root = engine.paths.get_static_path(default=True) / 'client'

        return static_file(fname, root=root)

    @get('/asset/<gmurl>/<url>/<fname>')
    def game_asset(gmurl, url, fname):
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

        # only allow specific file types
        if not fname.endswith('.png') and not fname.endswith('.mp3'):
            abort(404)

        # try to load asset file from disk
        root = engine.paths.get_game_path(gmurl, url)
        return static_file(fname, root)

