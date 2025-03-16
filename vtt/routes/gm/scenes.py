"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

from bottle import *


def register(engine: any):

    @post('/vtt/hashtest/<gm_url>/<game_url>')
    def post_image_hashtest(gm_url: str, game_url: str):
        # load GM from cache
        gm_cache = engine.cache.get_from_url(gm_url)
        if gm_cache is None:
            abort(404)

        # load game from cache
        game_cache = gm_cache.get_from_url(game_url)
        if game_cache is None:
            abort(404)

        # load game from GM's database to upload files
        game = gm_cache.db.Game.select(lambda g: g.url == game_url).first()
        if game is None:
            abort(404)

        # query urls for given md5 hashes
        known_urls = list()
        for md5 in request.forms.getall('hashs[]'):
            if md5 is not None:
                img_id = engine.storage.md5.get_id(game.gm_url, game.url, md5)

                if img_id is not None:
                    game_url = game.get_image_url(img_id)
                    known_urls.append(game_url)

        return {'urls': known_urls}

    @post('/vtt/upload-background/<gm_url>/<game_url>')
    def post_set_background(gm_url: str, game_url: str):
        client_ip = engine.get_client_ip(request)

        gm = engine.main_db.GM.load_from_session(request)
        if gm is None:
            engine.logging.warning(f'GM url="{gm_url}" tried set the background at the game {game_url} '
                                   f'by {client_ip} but is not the GM')
            abort(404)

        # load GM from cache
        gm_cache = engine.cache.get(gm)
        if gm_cache is None:
            engine.logging.warning(f'GM name="{gm.name}" url="{gm.url}" tried set the background at the game '
                                   f'{game_url} by {client_ip} but he was not inside the cache')
            abort(404)

        # load game from GM's database
        game = gm_cache.db.Game.select(lambda g: g.url == game_url).first()
        if game is None:
            engine.logging.warning(f'GM name="{gm.name}" url="{gm.url}" tried set the background at the game '
                                   f'{game_url} by {client_ip} but game was not found')
            abort(404)

        # load scene
        scene = gm_cache.db.Scene.select(lambda scn: scn.id == game.active).first()
        if scene is None:
            abort(404)

        # expect single background to be uploaded
        files = request.files.getall('file[]')
        if len(files) != 1:
            engine.logging.warning(f'GM name="{gm.name}" url="{gm.url}" tried set the background at the game '
                                   f'{game_url} by {client_ip} but did not provide a single image')
            abort(403)  # Forbidden

        # check mime type
        handle = files[0]
        content = handle.content_type.split('/')[0]
        if content != 'image':
            engine.logging.warning(f'GM name="{gm.name}" url="{gm.url}" tried set the background at the '
                                   f'game {game_url} by {client_ip} but used an unsupported type')
            abort(403)  # Forbidden

        # check file size
        max_file_size = engine.file_limit['background']
        size = engine.get_size(handle)
        if size > max_file_size * 1024 * 1024:
            engine.logging.warning(f'GM name="{gm.name}" url="{gm.url}" tried set the background at the '
                                   f'game {game_url} by {client_ip} but file was too large')
            abort(403)  # Forbidden

        # upload image
        img_url = game.upload(handle)
        return img_url

    @post('/vtt/query-scenes/<game_url>')
    @view('game/scenes')
    def post_create_scene(game_url: str):
        client_ip = engine.get_client_ip(request)

        gm = engine.main_db.GM.load_from_session(request)
        if gm is None:
            abort(404)

        # load GM from cache
        gm_cache = engine.cache.get(gm)
        if gm_cache is None:
            engine.logging.warning(f'GM name="{gm.name}" url="{gm.url}" tried create a scene at game {game_url} '
                                   f'by {client_ip} but he was not inside the cache')
            abort(404)

        # load game from GM's database
        game = gm_cache.db.Game.select(lambda g: g.url == game_url).first()
        if game is None:
            engine.logging.warning(f'GM name="{gm.name}" url="{gm.url}" tried create a scene at game {game_url} '
                                   f'by {client_ip} but game was not found')
            abort(404)

        return dict(engine=engine, game=game)
