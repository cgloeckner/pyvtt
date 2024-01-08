"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

from bottle import *


def register(engine: any):

    @post('/vtt/import-game/')
    @post('/vtt/import-game/<game_url>')
    def post_import_game(game_url: str | None = None):
        client_ip = engine.get_client_ip(request)

        status = {
            'url_ok': False,
            'file_ok': False,
            'error': '',
            'url': ''
        }

        # check GM
        gm = engine.main_db.GM.load_from_session(request)
        if gm is None:
            abort(404)

        # load GM from cache
        gm_cache = engine.cache.get(gm)

        if game_url is None:
            # pick random nonsense
            # @NOTE: the set of possible URLs is huge. we just play with
            # not having a collision, else the game creation would fail
            # and an error would be reported anyway
            game_url = engine.url_generator()

        else:
            # trim url length, convert to lowercase and trim whitespaces
            game_url = game_url[:30].lower().strip()

            # url
            if not engine.verify_url_section(game_url):
                engine.logging.warning(f'GM name="{gm.name}" url={gm.url} tried to import game by {client_ip} '
                                       f'but game url "{game_url}" is invalid')
                status['error'] = 'NO SPECIAL CHARS OR SPACES'
                return status

            if gm_cache.db.Game.select(lambda g: g.url == game_url).first() is not None:
                engine.logging.warning(f'GM name="{gm.name}" url={gm.url} tried to import game by {client_ip} '
                                       f'but game url "{game_url}" already in use')
                status['error'] = 'ALREADY IN USE'
                return status

        status['url_ok'] = True

        # upload file
        files = files = request.files.getall('file')
        if len(files) != 1:
            engine.logging.warning(f'GM name="{gm.name}" url={gm.url} tried to import game by {client_ip} '
                                   f'but uploaded {len(files)} files')
            status['error'] = 'ONE FILE AT ONCE'
            return status

        # query file size
        size = engine.get_size(files[0])

        filename = files[0].filename
        is_zip = filename.endswith('zip')
        if is_zip:
            # test zip file size
            limit = engine.file_limit['game']
            if size <= limit * 1024 * 1024:
                game = gm_cache.db.Game.from_zip(gm, game_url, files[0])
                if game is None:
                    engine.logging.access(f'GM name="{gm.name}" url={gm.url} tried to import game by {client_ip} '
                                          f'but the ZIP was invalid')
                    status['error'] = 'CORRUPTED FILE'.format(limit)
                    return status
            else:
                engine.logging.warning(f'GM name="{gm.name}" url={gm.url} tried to import game by {client_ip} '
                                       f'but tried to cheat on the file size')
                status['error'] = 'TOO LARGE GAME (MAX {0} MiB)'.format(limit)
                return status
        else:
            # test background file size
            limit = engine.file_limit['background']
            if size <= limit * 1024 * 1024:
                game = gm_cache.db.Game.from_image(gm, game_url, files[0])
            else:
                engine.logging.warning(f'GM name="{gm.name}" url={gm.url} tried to import game by {client_ip} '
                                       f'but tried to cheat on the file size')
                status['error'] = 'TOO LARGE BACKGROUND (MAX {0} MiB)'.format(limit)
                return status

        status['file_ok'] = game is not None
        if not status['file_ok']:
            engine.logging.warning(f'GM name="{gm.name}" url={gm.url} tried to import game by {client_ip} '
                                   f'but uploaded neither an image nor a zip file')
            status['error'] = 'USE AN IMAGE FILE'
            return status

        if is_zip:
            engine.logging.access(f'Game {game_url} imported from "{filename}" by {client_ip}')
        else:
            engine.logging.access(f'Game {game_url} created from "{filename}" by {client_ip}')

        status['url'] = f'game/{game.get_url()}'

        return status

    @get('/vtt/export-game/<game_url>')
    def export_game(game_url: str):
        client_ip = engine.get_client_ip(request)

        gm = engine.main_db.GM.load_from_session(request)
        if gm is None:
            abort(404)

        # load GM from cache
        gm_cache = engine.cache.get(gm)
        if gm_cache is None:
            engine.logging.warning(f'GM name="{gm.name}" url="{gm.url}" tried to export game {game_url} '
                                   f'by {client_ip} but he was not inside the cache')
            abort(404)

        # load game from GM's database
        game = gm_cache.db.Game.select(lambda g: g.url == game_url).first()
        if game is None:
            engine.logging.warning(f'GM name="{gm.name}" url="{gm.url}" tried to export game {game_url} '
                                   f'by {client_ip} but game was not found')
            abort(404)

        # export game to zip-file
        zip_file, zip_path = game.to_zip()

        engine.logging.access(f'Game {game_url} exported by {client_ip}')

        # offer file for downloading
        return static_file(zip_file, root=zip_path, download=zip_file, mimetype='application/zip')
