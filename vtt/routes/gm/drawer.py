"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

from bottle import *


def register(engine):

    @get('/')
    @view('gm')
    def get_game_list():
        gm = engine.main_db.GM.load_from_session(request)
        if gm is None:
            # remove cookie
            # FIXME: setting cookie is ignored on redirect
            response.set_cookie('session', '', path='/', max_age=1, secure=engine.has_ssl())
            redirect('/vtt/join')

        # load GM from cache
        gm_cache = engine.cache.get(gm)
        if gm_cache is None:
            # remove cookie
            engine.logging.warning \
                ('GM name="{0}" url={1} tried to relogin by {2} but he was not in the cache'.format(gm.name, gm.url, engine.get_client_ip
                                                                                                       (request)))
            response.set_cookie('session', '', path='/', max_age=1, secure=engine.has_ssl())
            abort(404)

        # refresh session
        gm.refresh_session(response)

        engine.logging.access \
            ('GM name="{0}" url={1} session refreshed by {2}'.format(gm.name, gm.url, engine.get_client_ip(request)))

        server = ''

        # load game from GM's database
        all_games = gm_cache.db.Game.select()

        # show GM's games
        return dict(engine=engine, gm=gm, all_games=all_games, server=server)

    @get('/vtt/fancy-url')
    def call_fancy_url():
        return engine.url_generator()

    @post('/vtt/clean-up/<url>')
    def clean_up(url):
        gm = engine.main_db.GM.load_from_session(request)
        if gm is None:
            abort(404)

        # load GM from cache
        gm_cache = engine.cache.get(gm)
        if gm_cache is None:
            engine.logging.warning \
                ('GM name="{0}" url="{1}" tried to kick all players at {2} by {3} but he was not inside the cache'.format
                    (gm.name, gm.url, url, engine.get_client_ip(request)))
            abort(404)

        # load game from GM's database
        game = gm_cache.db.Game.select(lambda g: g.url == url).first()
        if game is None:
            engine.logging.warning \
                ('GM name="{0}" url="{1}" tried to kick all players at {2} by {3} but game was not found'.format(gm.name, gm.url, url, engine.get_client_ip
                                                                                                                    (request)))
            abort(404)

        # load game from cache and clean it up
        now = time.time()
        game_cache = gm_cache.get(game)
        game.cleanup(now) # cleanup old images and tokens
        game_cache.cleanup() # remove all players

        engine.logging.access('Players kicked from {0} by {1}'.format(game.get_url(), engine.get_client_ip(request)))

    @post('/vtt/kick-player/<url>/<uuid>')
    def kick_player(url, uuid):
        gm = engine.main_db.GM.load_from_session(request)
        if gm is None:
            abort(404)

        # load GM from cache
        gm_cache = engine.cache.get(gm)
        if gm_cache is None:
            engine.logging.warning(
                'GM name="{0}" url="{1}" tried to kick player #{4} at {2} by {3} but he was not inside the cache'.format(
                    gm.name, gm.url, url, engine.get_client_ip(request), uuid))
            abort(404)

        # load game from GM's database
        game = gm_cache.db.Game.select(lambda g: g.url == url).first()
        if game is None:
            engine.logging.warning(
                'GM name="{0}" url="{1}" tried to kick players #{4} {2} by {3} but game was not found'.format(gm.name,
                                                                                                              gm.url,
                                                                                                              url,
                                                                                                              engine.get_client_ip(
                                                                                                                  request),
                                                                                                              uuid))
            abort(404)

        # fetch game cache and close sockets
        game_cache = gm_cache.get(game)
        if game_cache is None:
            engine.logging.warning(
                'GM name="{0}" url="{1}" tried to kick player #{4} at {2} by {3} but the game was not inside the cache'.format(
                    gm.name, gm.url, url, engine.get_client_ip(request), uuid))
            abort(404)

        name = game_cache.disconnect(uuid)

        engine.logging.access(
            'Player {0} ({1}) kicked from {2} by {3}'.format(name, uuid, game.get_url(), engine.get_client_ip(request)))

    @post('/vtt/delete-game/<url>')
    @view('gms/games')
    def delete_game(url):
        gm = engine.main_db.GM.load_from_session(request)
        if gm is None:
            abort(404)

        # load GM from cache
        gm_cache = engine.cache.get(gm)
        if gm_cache is None:
            engine.logging.warning(
                'GM name="{0}" url="{1}" tried delete the game {2} by {3} but he was not inside the cache'.format(
                    gm.name, gm.url, url, engine.get_client_ip(request)))
            abort(404)

        # load game from GM's database
        game = gm_cache.db.Game.select(lambda g: g.url == url).first()
        if game is None:
            engine.logging.warning(
                'GM name="{0}" url="{1}" tried delete the game {2} by {3} but game was not found'.format(gm.name,
                                                                                                         gm.url, url,
                                                                                                         engine.get_client_ip(
                                                                                                             request)))
            abort(404)

        # delete everything for that game
        game.pre_delete()
        game.delete()

        engine.logging.access('Game {0} deleted by {1}'.format(game.get_url(), engine.get_client_ip(request)))

        # load game from GM's database
        all_games = gm_cache.db.Game.select()

        server = ''

        return dict(gm=gm, server=server, all_games=all_games)
