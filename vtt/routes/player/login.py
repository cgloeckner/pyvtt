"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

from bottle import *


def register(engine):
    @get('/vtt/schedule/<timestamp>')
    @view('countdown')
    def vtt_countdown(timestamp):
        return dict(engine=engine, timestamp=timestamp)

    @post('/game/<gmurl>/<url>/login')
    def set_player_name(gmurl, url):
        result = {
            'uuid': '',
            'is_gm': False,
            'playername': '',
            'playercolor': '',
            'error': ''
        }

        playername = template('{{value}}', value=format(request.forms.playername))
        playercolor = request.forms.get('playercolor')

        # load GM from cache
        gm_cache = engine.cache.getFromUrl(gmurl)
        if gm_cache is None:
            engine.logging.warning(
                'Player tried to login {0} by {1}, but GM was not found.'.format(gmurl, engine.getClientIp(request)))
            result['error'] = 'GAME NOT FOUND'
            return result

        # load game from GM's database
        game = gm_cache.db.Game.select(lambda g: g.url == url).first()
        if game is None:
            engine.logging.warning('Player tried to login {0}/{1} by {2}, but game was not found.'.format(gmurl, url,
                                                                                                          engine.getClientIp(
                                                                                                              request)))
            result['error'] = 'GAME NOT FOUND'
            return result

        if playername == '':
            engine.logging.warning(
                'Player tried to login {0} by {1}, but did not provide a username.'.format(game.getUrl(),
                                                                                           engine.getClientIp(request)))
            result['error'] = 'PLEASE ENTER A NAME'
            return result

        # limit length, trim whitespaces
        playername = playername[:30].strip()

        # @NOTE: this feature isn't really required anymore
        """
        # make player color less bright
        parts       = [int(playercolor[1:3], 16), int(playercolor[3:5], 16), int(playercolor[5:7], 16)]
        playercolor = '#'
        for c in parts:
            if c > 200:
                c = 200
            if c < 16:
                playercolor += '0'
            playercolor += hex(c)[2:]
        """

        # check for player name collision
        game_cache = gm_cache.get(game)
        if game_cache is None:
            engine.logging.warning(
                'Player tried to login {0} by {1}, but game was not in the cache.'.format(game.getUrl(),
                                                                                          engine.getClientIp(request)))
            result['error'] = 'GAME NOT FOUND'
            return result

        # query whether user is the hosting GM
        session_gm = engine.main_db.GM.loadFromSession(request)
        gm_is_host = session_gm is not None and session_gm.url == gmurl

        # kill all timeout players and login this new player
        try:
            player_cache = game_cache.insert(playername, playercolor, is_gm=gm_is_host)
        except KeyError:
            engine.logging.warning(
                'Player tried to login {0} by {1}, but username "{2}" is already in use.'.format(game.getUrl(),
                                                                                                 engine.getClientIp(
                                                                                                     request),
                                                                                                 playername))
            result['error'] = 'ALREADY IN USE'
            return result

        # save playername in client cookie
        expire = int(time.time() + engine.cleanup['expire'])
        response.set_cookie('playername', playername, path=game.getUrl(), expires=expire, secure=engine.hasSsl())
        response.set_cookie('playercolor', playercolor, path=game.getUrl(), expires=expire, secure=engine.hasSsl())

        engine.logging.access('Player logged in to {0} by {1}.'.format(game.getUrl(), engine.getClientIp(request)))

        result['playername'] = player_cache.name
        result['playercolor'] = player_cache.color
        result['uuid'] = player_cache.uuid
        result['is_gm'] = player_cache.is_gm
        return result
