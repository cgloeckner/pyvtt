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

    @get('/game/<gmurl>/<url>')
    @get('/game/<gmurl>/<url>/<timestamp>')
    @view('battlemap')
    def get_player_battlemap(gmurl, url, timestamp=None):
        gm = engine.main_db.GM.loadFromSession(request)

        # try to load playername from cookie (or from GM name)
        playername = request.get_cookie('playername', default='')

        # query whether user is the hosting GM
        session_gm = engine.main_db.GM.loadFromSession(request)
        you_are_host = session_gm is not None and session_gm.url == gmurl

        # query gm of that game
        host = engine.main_db.GM.select(lambda gm: gm.url == gmurl).first()
        if host is None:
            abort(404)

        # try to load playercolor from cookieplayercolor = request.get_cookie('playercolor')
        playercolor = request.get_cookie('playercolor')
        if playercolor is None:
            colors = engine.playercolors
            playercolor = colors[random.randrange(len(colors))]

        # load GM from cache
        gm_cache = engine.cache.getFromUrl(gmurl)
        if gm_cache is None:
            abort(404)

        # load game from GM's database
        game = gm_cache.db.Game.select(lambda g: g.url == url).first()
        if game is None:
            abort(404)

        websocket_url = engine.getWebsocketUrl()

        supported_dice = engine.getSupportedDice()
        if 100 in supported_dice:
            supported_dice.remove(100)
        supported_dice.reverse()

        # show battlemap with login screen ontop
        return dict(engine=engine, websocket_url=websocket_url, game=game, playername=playername, playercolor=playercolor,
                    host=host, gm=gm, dice=supported_dice, timestamp=timestamp)

    @post('/game/<gmurl>/<url>/upload')
    def post_image_upload(gmurl, url):
        # load GM from cache
        gm_cache = engine.cache.getFromUrl(gmurl)
        if gm_cache is None:
            abort(404)

        # loda game from cache
        game_cache = gm_cache.getFromUrl(url)
        if game_cache is None:
            abort(404)

        # load game from GM's database to upload files
        answer = {'urls': list(), 'music': list()};
        game = gm_cache.db.Game.select(lambda g: g.url == url).first()
        if game is None:
            abort(404)

        # load active scene
        scene = gm_cache.db.Scene.select(lambda s: s.id == game.active).first()
        if scene is None:
            abort(404)

        background_set = scene.backing is not None
        # query file sizes
        try:
            files = request.files.getall('file[]')
        except OSError:
            # cannot read uploaded files
            abort(404)

        for i, handle in enumerate(files):
            content = handle.content_type.split('/')[0]

            # check image size
            if content == 'image':
                max_filesize = engine.file_limit['token']
                if i == 0 and not background_set:
                    max_filesize = engine.file_limit['background']
                # determine file size
                size = engine.getSize(handle)
                # check filesize
                if size > max_filesize * 1024 * 1024:
                    engine.logging.warning(
                        'Player tried to upload an image to a game by {0} but tried to cheat on the filesize'.format(
                            engine.getClientIp(request), url))
                    abort(403)  # Forbidden

            # check audio size
            elif content == 'audio':
                max_filesize = engine.file_limit['music']
                # determine file size
                size = engine.getSize(handle)
                # check filesize
                if size > max_filesize * 1024 * 1024:
                    engine.logging.warning(
                        'Player tried to upload music to a game by {0} but tried to cheat on the filesize'.format(
                            engine.getClientIp(request), url))
                    abort(403)  # Forbidden

            # unsupported filetype
            else:
                engine.logging.warning(
                    'Player tried to "{1}" to a game by {0} which is unsupported'.format(engine.getClientIp(request),
                                                                                         handle.content_type))
                abort(403)  # Forbidden

        # upload files
        for handle in files:
            content = handle.content_type.split('/')[0]

            # check image size
            if content == 'image':
                img_url = game.upload(handle)
                if img_url is not None:
                    answer['urls'].append(img_url)
                    engine.logging.access('Image upload {0} by {1}'.format(url, engine.getClientIp(request)))
                else:
                    engine.logging.access('Image failed to upload by {0}'.format(engine.getClientIp(request)))

            # upload music
            elif content == 'audio':
                slot_id = game_cache.uploadMusic(handle)
                answer['music'].append(slot_id)

        # return urls
        # @NOTE: request was non-JSON to allow upload, so urls need to be encoded

        return json.dumps(answer)

    @get('/vtt/websocket')
    def accept_websocket():
        socket = request.environ.get('wsgi.websocket')

        if socket is not None:
            player_cache = engine.cache.listen(socket)
            if player_cache is None:
                return
            # wait until greenlet is closed
            # @NOTE: this keeps the websocket open
            greenlet = player_cache.greenlet
            try:
                greenlet.get()
            except Exception as error:
                error.metadata = player_cache.getMetaData()
                # reraise greenlet's exception to trigger proper error reporting
                raise error
