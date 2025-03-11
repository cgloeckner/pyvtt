"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

from bottle import *


def register(engine: any):

    @get('/vtt/schedule/<timestamp>')
    @view('countdown')
    def vtt_countdown(timestamp: str):
        return dict(engine=engine, timestamp=timestamp)

    @post('/game/<gm_url>/<game_url>/login')
    def set_player_name(gm_url: str, game_url: str):
        client_ip = engine.get_client_ip(request)

        result = {
            'uuid': '',
            'is_gm': False,
            'playername': '',
            'playercolor': '',
            'error': ''
        }

        player_name = template('{{value}}', value=format(request.forms.playername))
        player_color = request.forms.get('playercolor')

        # load GM from cache
        gm_cache = engine.cache.get_from_url(gm_url)
        if gm_cache is None:
            engine.logging.warning(f'Player tried to login {gm_url} by {client_ip}, but GM was not found.')
            result['error'] = 'GAME NOT FOUND'
            return result

        # load game from GM's database
        game = gm_cache.db.Game.select(lambda g: g.url == game_url).first()
        if game is None:
            engine.logging.warning(f'Player tried to login {gm_url}/{game_url} by {client_ip}, but game was not found.')
            result['error'] = 'GAME NOT FOUND'
            return result

        if player_name == '':
            engine.logging.warning(f'Player tried to login {game_url} by {client_ip}, but did not provide a username.')
            result['error'] = 'PLEASE ENTER A NAME'
            return result

        # limit length, trim whitespaces
        player_name = player_name[:30].strip()

        # check for player name collision
        game_cache = gm_cache.get(game)
        if game_cache is None:
            engine.logging.warning(f'Player tried to login {game_url} by {client_ip}, but game was not in the cache.')
            result['error'] = 'GAME NOT FOUND'
            return result

        # query whether user is the hosting GM
        session_gm = engine.main_db.GM.load_from_session(request)
        gm_is_host = session_gm is not None and session_gm.url == gm_url

        # kill all timeout players and login this new player
        try:
            player_cache = game_cache.insert(player_name, player_color, is_gm=gm_is_host)
        except KeyError:
            engine.logging.warning(f'Player tried to login {game_url} by {client_ip}, but username "{player_name}"'
                                   f' is already in use.')
            result['error'] = 'ALREADY IN USE'
            return result

        # save playername in client cookie
        expire = int(time.time() + engine.cleanup['expire'])
        response.set_cookie('playername', player_name, path=game.get_url(), expires=expire, secure=engine.has_ssl())
        response.set_cookie('playercolor', player_color, path=game.get_url(), expires=expire, secure=engine.has_ssl())

        engine.logging.access(f'Player logged in to {game_url} by {client_ip}.')

        result['playername'] = player_cache.name
        result['playercolor'] = player_cache.color
        result['uuid'] = player_cache.uuid
        result['is_gm'] = player_cache.is_gm
        return result
