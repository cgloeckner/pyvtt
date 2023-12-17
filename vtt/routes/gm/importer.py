"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

from bottle import *


def register(engine):

    @post('/vtt/import-game/')
    @post('/vtt/import-game/<url>')
    def post_import_game(url=None):
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

        if url is None:
            # pick random nonsense
            # @NOTE: the set of possible URLs is huge. we just play with
            # not having a collision, else the game creation would fail
            # and an error would be reported anyway
            url = engine.url_generator()

        else:
            # trim url length, convert to lowercase and trim whitespaces
            url = url[:30].lower().strip()

            # url
            if not engine.verify_url_section(url):
                engine.logging.warning \
                    ('GM name="{0}" url={1} tried to import game by {2} but game url "{3}" is invalid'.format(gm.name,
                                                                                                              gm.url,
                                                                                                              engine.get_client_ip
                                                                                                              (request),
                                                                                                              url))
                status['error'] = 'NO SPECIAL CHARS OR SPACES'
                return status

            if gm_cache.db.Game.select(lambda g: g.url == url).first() is not None:
                engine.logging.warning \
                    ('GM name="{0}" url={1} tried to import game by {2} but game url "{3}" already in use'.format(gm.name,
                                                                                                                  gm.url,
                                                                                                                  engine.get_client_ip
                                                                                                                  (request),
                                                                                                                  url))
                status['error'] = 'ALREADY IN USE'
                return status

        status['url_ok'] = True

        # upload file
        try:
            files = request.files.getall('file')
        except OSError:
            # cannot read uploaded files
            abort(404)

        if len(files) != 1:
            engine.logging.warning \
                ('GM name="{0}" url={1} tried to import game by {2} but uploaded {3} files'.format(gm.name, gm.url,
                                                                                                   engine.get_client_ip
                                                                                                   (request), len(files)))
            status['error'] = 'ONE FILE AT ONCE'
            return status

        # query filesize
        size = engine.get_size(files[0])

        fname = files[0].filename
        is_zip = fname.endswith('zip')
        if is_zip:
            # test zip file size
            limit = engine.file_limit['game']
            if size <= limit * 1024 * 1024:
                game = gm_cache.db.Game.from_zip(gm, url, files[0])
                if game is None:
                    engine.logging.access \
                        ('GM name="{0}" url={1} tried to import game by {2} but the ZIP was invalid'.format(gm.name, gm.url,
                                                                                                            engine.get_client_ip
                                                                                                            (request), url))
                    status['error'] = 'CORRUPTED FILE'.format(limit)
                    return status
            else:
                engine.logging.warning \
                    ('GM name="{0}" url={1} tried to import game by {2} but tried to cheat on the filesize'.format(gm.name,
                                                                                                                   gm.url,
                                                                                                                   engine.get_client_ip
                                                                                                                   (request),
                                                                                                                   url))
                status['error'] = 'TOO LARGE GAME (MAX {0} MiB)'.format(limit)
                return status
        else:
            # test background file size
            limit = engine.file_limit['background']
            if size <= limit * 1024 * 1024:
                game = gm_cache.db.Game.from_image(gm, url, files[0])
            else:
                engine.logging.warning \
                    ('GM name="{0}" url={1} tried to import game by {2} but tried to cheat on the filesize'.format(gm.name,
                                                                                                                   gm.url,
                                                                                                                   engine.get_client_ip
                                                                                                                   (request),
                                                                                                                   url))
                status['error'] = 'TOO LARGE BACKGROUND (MAX {0} MiB)'.format(limit)
                return status

        status['file_ok'] = game is not None
        if not status['file_ok']:
            engine.logging.warning \
                ('GM name="{0}" url={1} tried to import game by {2} but uploaded neither an image nor a zip file'.format
                 (gm.name, gm.url, engine.get_client_ip(request), url))
            status['error'] = 'USE AN IMAGE FILE'
            return status

        if is_zip:
            engine.logging.access \
                ('Game {0} imported from "{1}" by {2}'.format(game.get_url(), fname, engine.get_client_ip(request)))
        else:
            engine.logging.access \
                ('Game {0} created from "{1}" by {2}'.format(game.get_url(), fname, engine.get_client_ip(request)))

        status['url'] = f'game/{game.get_url()}'

        return status


    @get('/vtt/export-game/<url>')
    def export_game(url):
        gm = engine.main_db.GM.load_from_session(request)
        if gm is None:
            abort(404)

        # load GM from cache
        gm_cache = engine.cache.get(gm)
        if gm_cache is None:
            engine.logging.warning \
                ('GM name="{0}" url="{1}" tried to export game {2} by {3} but he was not inside the cache'.format(gm.name,
                                                                                                                  gm.url,
                                                                                                                  url,
                                                                                                                  engine.get_client_ip
                                                                                                                  (request)))
            abort(404)

        # load game from GM's database
        game = gm_cache.db.Game.select(lambda g: g.url == url).first()
        if game is None:
            engine.logging.warning \
                ('GM name="{0}" url="{1}" tried to export game {2} by {3} but game was not found'.format(gm.name, gm.url,
                                                                                                         url,
                                                                                                         engine.get_client_ip
                                                                                                         (request)))
            abort(404)

        # export game to zip-file
        zip_file, zip_path = game.to_zip()

        engine.logging.access('Game {0} exported by {1}'.format(game.get_url(), engine.get_client_ip(request)))

        # offer file for downloading
        return static_file(zip_file, root=zip_path, download=zip_file, mimetype='application/zip')
