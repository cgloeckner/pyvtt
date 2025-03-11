"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

from bottle import *


def register(engine: any):

    @get('/')
    @view('gm')
    def get_game_list():
        client_ip = engine.get_client_ip(request)

        gm = engine.main_db.GM.load_from_session(request)
        if gm is None:
            # remove cookie
            # FIXME: setting cookie is ignored on redirect
            response.set_cookie('session', '', path='/', max_age=1, secure=engine.uses_https())
            redirect('/vtt/join')

        # load GM from cache
        gm_cache = engine.cache.get(gm)
        if gm_cache is None:
            # remove cookie
            engine.logging.warning(f'GM name="{gm.name}" url={gm.url} tried to re-login by {client_ip} '
                                   f'but he was not in the cache')
            response.set_cookie('session', '', path='/', max_age=1, secure=engine.uses_https())
            abort(404)

        # refresh session
        gm.refresh_session(response)

        engine.logging.access(f'GM name="{gm.name}" url={gm.url} session refreshed by {client_ip}')

        server = ''

        # load game from GM's database
        all_games = gm_cache.db.Game.select()

        # show GM's games
        return dict(engine=engine, gm=gm, all_games=all_games, server=server)

    @get('/vtt/fancy-url')
    def call_fancy_url():
        return engine.url_generator()

    @post('/vtt/clean-up/<game_url>')
    def clean_up(game_url: str):
        client_ip = engine.get_client_ip(request)

        gm = engine.main_db.GM.load_from_session(request)
        if gm is None:
            abort(404)

        # load GM from cache
        gm_cache = engine.cache.get(gm)
        if gm_cache is None:
            engine.logging.warning(f'GM name="{gm.name}" url="{gm.url}" tried to kick all players at {game_url} '
                                   f'by {client_ip} but he was not inside the cache')
            abort(404)

        # load game from GM's database
        game = gm_cache.db.Game.select(lambda g: g.url == game_url).first()
        if game is None:
            engine.logging.warning(f'GM name="{gm.name}" url="{gm.url}" tried to kick all players at {game_url} '
                                   f'by {client_ip} but game was not found')
            abort(404)

        # load game from cache and clean it up
        now = time.time()
        game_cache = gm_cache.get(game)
        game.cleanup(now)  # cleanup old images and tokens
        game_cache.cleanup()  # remove all players

        engine.logging.access(f'Players kicked from {game.get_url()} by {client_ip}')

    @post('/vtt/kick-player/<game_url>/<uuid>')
    def kick_player(game_url: str, uuid: str):
        client_ip = engine.get_client_ip(request)

        gm = engine.main_db.GM.load_from_session(request)
        if gm is None:
            abort(404)

        # load GM from cache
        gm_cache = engine.cache.get(gm)
        if gm_cache is None:
            engine.logging.warning(f'GM name="{gm.name}" url="{gm.url}" tried to kick player #{uuid} at {game_url} '
                                   f'by {client_ip} but he was not inside the cache')
            abort(404)

        # load game from GM's database
        game = gm_cache.db.Game.select(lambda g: g.url == game_url).first()
        if game is None:
            engine.logging.warning(f'GM name="{gm.name}" url="{gm.url}" tried to kick players #{uuid} {game_url} '
                                   f'by {client_ip} but game was not found')
            abort(404)

        # fetch game cache and close sockets
        game_cache = gm_cache.get(game)
        if game_cache is None:
            engine.logging.warning(f'GM name="{gm.name}" url="{gm.url}" tried to kick player #{uuid} at {game_url} '
                                   f'by {client_ip} but the game was not inside the cache')
            abort(404)

        name = game_cache.disconnect(uuid)

        engine.logging.access(f'Player {name} ({uuid}) kicked from {game_url} by {client_ip}')

    @post('/vtt/delete-game/<game_url>')
    @view('gms/games')
    def delete_game(game_url: str):
        client_ip = engine.get_client_ip(request)

        gm = engine.main_db.GM.load_from_session(request)
        if gm is None:
            abort(404)

        # load GM from cache
        gm_cache = engine.cache.get(gm)
        if gm_cache is None:
            engine.logging.warning(f'GM name="{gm.name}" url="{gm.url}" tried delete the game {game_url} '
                                   f'by {client_ip} but he was not inside the cache')
            abort(404)

        # load game from GM's database
        game = gm_cache.db.Game.select(lambda g: g.url == game_url).first()
        if game is None:
            engine.logging.warning(f'GM name="{gm.name}" url="{gm.url}" tried delete the game {game_url} '
                                   f'by {client_ip} but game was not found')
            abort(404)

        # delete everything for that game
        game.pre_delete()
        game.delete()

        engine.logging.access(f'Game {game_url} deleted by {client_ip}')

        # load game from GM's database
        all_games = gm_cache.db.Game.select()

        server = ''

        return dict(gm=gm, server=server, all_games=all_games)
