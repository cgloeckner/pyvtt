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

    @get('/game/<gm_url>/<game_url>')
    @get('/game/<gm_url>/<game_url>/<timestamp>')
    @view('battlemap')
    def get_player_battlemap(gm_url, game_url, timestamp: str | None = None):
        gm = engine.main_db.GM.load_from_session(request)

        # try to load playername from cookie (or from GM name)
        player_name = request.get_cookie('playername', default='')

        # query gm of that game
        game_host = engine.main_db.GM.select(lambda _gm: _gm.url == gm_url).first()
        if game_host is None:
            abort(404)

        # try to load player color from cookie
        player_color = request.get_cookie('playercolor')
        if player_color is None:
            colors = engine.playercolors
            player_color = colors[random.randrange(len(colors))]

        # load GM from cache
        gm_cache = engine.cache.get_from_url(gm_url)
        if gm_cache is None:
            abort(404)

        # load game from GM's database
        game = gm_cache.db.Game.select(lambda g: g.url == game_url).first()
        if game is None:
            abort(404)

        websocket_url = engine.get_websocket_url()

        supported_dice = engine.get_supported_dice()
        if 100 in supported_dice:
            supported_dice.remove(100)
        supported_dice.reverse()

        # show battle map with login screen on top
        return dict(engine=engine, websocket_url=websocket_url, game=game, playername=player_name,
                    playercolor=player_color, host=game_host, gm=gm, dice=supported_dice, timestamp=timestamp)

    @post('/game/<gm_url>/<game_url>/upload')
    def post_image_upload(gm_url: str, game_url: str):
        client_ip = engine.get_client_ip(request)

        # load GM from cache
        gm_cache = engine.cache.get_from_url(gm_url)
        if gm_cache is None:
            abort(404)

        # load game from cache
        game_cache = gm_cache.get_from_url(game_url)
        if game_cache is None:
            abort(404)

        # load game from GM's database to upload files
        answer = {'urls': list(), 'music': list()}
        game = gm_cache.db.Game.select(lambda g: g.url == game_url).first()
        if game is None:
            abort(404)

        # load active scene
        scene = gm_cache.db.Scene.select(lambda scn: scn.id == game.active).first()
        if scene is None:
            abort(404)

        background_set = scene.backing is not None
        file_list = list()
        # query file sizes
        try:
            file_list = request.files.getall('file[]')
        except OSError:
            # cannot read uploaded files
            abort(404)

        for i, handle in enumerate(file_list):
            content = handle.content_type.split('/')[0]

            # check image size
            if content == 'image':
                max_file_size = engine.file_limit['token']
                if i == 0 and not background_set:
                    max_file_size = engine.file_limit['background']
                # determine file size
                size = engine.get_size(handle)
                # check file size
                if size > max_file_size * 1024 * 1024:
                    engine.logging.warning(f'Player {client_ip} tried to upload an image to a game by {game_url} '
                                           f'but tried to cheat on the file size')
                    abort(403)  # Forbidden

            # check audio size
            elif content == 'audio':
                max_file_size = engine.file_limit['music']
                # determine file size
                size = engine.get_size(handle)
                # check file size
                if size > max_file_size * 1024 * 1024:
                    engine.logging.warning(f'Player {client_ip} tried to upload music to a game by {game_url} '
                                           f'but tried to cheat on the file size')
                    abort(403)  # Forbidden

            # unsupported filetype
            else:
                engine.logging.warning(f'Player {client_ip} tried to upload "{handle.content_type}" to a game by '
                                       f'{game_url} which is unsupported')
                abort(403)  # Forbidden

        # upload files
        for handle in file_list:
            content = handle.content_type.split('/')[0]

            # check image size
            if content == 'image':
                img_url = game.upload(handle)
                if img_url is not None:
                    answer['urls'].append(img_url)
                    engine.logging.access(f'Image upload {game_url} by {client_ip}')
                else:
                    engine.logging.access(f'Image failed to upload by {client_ip}')

            # upload music
            elif content == 'audio':
                slot_id = game_cache.upload_music(handle)
                answer['music'].append(slot_id)

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
            except Exception as err:
                error.metadata = player_cache.get_meta_data()
                # reraise greenlet's exception to trigger proper error reporting
                raise err
