"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

from bottle import *


def register(engine):

    @post('/vtt/hashtest/<gmurl>/<url>')
    def post_image_hashtest(gmurl, url):
        # load GM from cache
        gm_cache = engine.cache.getFromUrl(gmurl)
        if gm_cache is None:
            abort(404)

        # loda game from cache
        game_cache = gm_cache.getFromUrl(url)
        if game_cache is None:
            abort(404)

        # load game from GM's database to upload files
        game = gm_cache.db.Game.select(lambda g: g.url == url).first()
        if game is None:
            abort(404)

        # query urls for given md5 hashes
        known_urls = list()
        for md5 in request.forms.getall('hashs[]'):
            if md5 is not None:
                imgid = game.getIdByMd5(md5)

                if imgid is not None:
                    url = game.getImageUrl(imgid)
                    known_urls.append(url)

        return {'urls': known_urls}


    @post('/vtt/upload-background/<gmurl>/<url>')
    def post_set_background(gmurl, url):
        gm = engine.main_db.GM.loadFromSession(request)
        if gm is None:
            engine.logging.warning(
                'GM url="{0}" tried set the background at the game {1} by {2} but is not the GM'.format(gmurl, url,
                                                                                                        engine.getClientIp(
                                                                                                            request)))
            abort(404)

        # load GM from cache
        gm_cache = engine.cache.get(gm)
        if gm_cache is None:
            engine.logging.warning(
                'GM name="{0}" url="{1}" tried set the background at the game {2} by {3} but he was not inside the cache'.format(
                    gm.name, gm.url, url, engine.getClientIp(request)))
            abort(404)

        # load game from GM's database
        game = gm_cache.db.Game.select(lambda g: g.url == url).first()
        if game is None:
            engine.logging.warning(
                'GM name="{0}" url="{1}" tried set the background at the game {2} by {3} but game was not found'.format(
                    gm.name, gm.url, url, engine.getClientIp(request)))
            abort(404)

        # load scene
        scene = gm_cache.db.Scene.select(lambda s: s.id == game.active).first()
        if scene is None:
            abort(404)

        # expect single background to be uploaded
        try:
            files = request.files.getall('file[]')
        except OSError:
            # cannot read uploaded files
            abort(404)

        if len(files) != 1:
            engine.logging.warning(
                'GM name="{0}" url="{1}" tried set the background at the game {2} by {3} but did not provide a single image'.format(
                    gm.name, gm.url, url, engine.getClientIp(request)))
            abort(403)  # Forbidden

        # check mime type
        handle = files[0]
        content = handle.content_type.split('/')[0]
        if content != 'image':
            engine.logging.warning(
                'GM name="{0}" url="{1}" tried set the background at the game {2} by {3} but used an unsupported type'.format(
                    gm.name, gm.url, url, engine.getClientIp(request)))
            abort(403)  # Forbidden

        # check file size
        max_filesize = engine.file_limit['background']
        size = engine.getSize(handle)
        if size > max_filesize * 1024 * 1024:
            engine.logging.warning(
                'GM name="{0}" url="{1}" tried set the background at the game {2} by {3} but file was too large'.format(
                    gm.name, gm.url, url, engine.getClientIp(request)))
            abort(403)  # Forbidden

        # upload image
        img_url = game.upload(handle)
        return img_url


    @post('/vtt/query-scenes/<url>')
    @view('game/scenes')
    def post_create_scene(url):
        gm = engine.main_db.GM.loadFromSession(request)
        if gm is None:
            abort(404)

        # load GM from cache
        gm_cache = engine.cache.get(gm)
        if gm_cache is None:
            engine.logging.warning(
                'GM name="{0}" url="{1}" tried create a scene at game {2} by {3} but he was not inside the cache'.format(
                    gm.name, gm.url, url, engine.getClientIp(request)))
            abort(404)

        # load game from GM's database
        game = gm_cache.db.Game.select(lambda g: g.url == url).first()
        if game is None:
            engine.logging.warning(
                'GM name="{0}" url="{1}" tried create a scene at game {2} by {3} but game was not found'.format(gm.name,
                                                                                                                gm.url, url,
                                                                                                                engine.getClientIp(
                                                                                                                    request)))
            abort(404)

        return dict(engine=engine, game=game)
