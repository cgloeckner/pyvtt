"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

import httpagentparser

from bottle import *

from vtt.utils.common import add_dict_set, count_dict_set_len


def register(engine):
    @get('/vtt/api/users')
    def api_query_users():
        now = time.time()

        # query gms
        total_gms = engine.main_db.GM.select().count()
        abandoned_gms = engine.main_db.GM.select(lambda g: g.timeid < now - engine.cleanup['expire']).count()

        # query games
        threshold = 10
        total_games = 0
        running_games = 0
        with engine.cache.lock:
            for gm in engine.cache.gms:
                gm_cache = engine.cache.gms[gm]
                with gm_cache.lock:
                    total_games += gm_cache.db.Game.select().count()
                    running_games += gm_cache.db.Game.select(lambda g: g.timeid >= now - threshold * 60).count()
        done = time.time()

        # return data
        return {
            'gms': {
                'total': total_gms,
                'abandoned': abandoned_gms
            },
            'games': {
                'total': total_games,
                'running': running_games
            },
            'query_time': done - now
        }

    @get('/vtt/api/games-list/<gmurl>')
    def api_games_list(gmurl):
        start = time.time()

        # load GM from cache
        gm_cache = engine.cache.get_from_url(gmurl)
        if gm_cache is None:
            # @NOTE: not logged because somebody may play around with this
            abort(404)

        # query whether user is the hosting GM
        session_gm = engine.main_db.GM.load_from_session(request)
        if session_gm is None or session_gm.url != gmurl:
            abort(404)

        data = {
            'games': []
        }
        for game in gm_cache.db.Game.select():
            data['games'].append(game.url)
        done = time.time()

        data['query_time'] = done - start
        return data

    @get('/vtt/api/assets-list/<gmurl>/<url>')
    def api_asset_list(gmurl, url):
        start = time.time()

        # load GM from cache
        gm_cache = engine.cache.get_from_url(gmurl)
        if gm_cache is None:
            # @NOTE: not logged because somebody may play around with this
            abort(404)

        # query whether user is the hosting GM
        session_gm = engine.main_db.GM.load_from_session(request)
        if session_gm is None or session_gm.url != gmurl:
            abort(404)

        # try to load game from GM's database
        game = gm_cache.db.Game.select(lambda g: g.url == url).first()
        root = ['./static/assets', engine.paths.get_assets_path()]
        if game is not None:
            root = [engine.paths.get_game_path(gmurl, url)]

        files = {
            'images': [],
            'audio': []
        }
        for subroot in root:
            for fname in os.listdir(subroot):
                if fname.endswith('.png'):
                    files['images'].append(fname)
                if fname.endswith('.mp3'):
                    files['audio'].append(fname)
        if game is not None:
            files['images'].sort(key=lambda k: int(k.split('.')[0]))
        else:
            files['images'].sort()
        files['audio'].sort()
        done = time.time()

        files['query_time'] = done - start

        return files

    @get('/vtt/api/cleanup')
    def api_next_cleanup():
        when, until = engine.cleanup_worker.getNextUpdate()
        return {
            'server time': str(when),
            'time left': str(until)
        }

    @get('/vtt/api/build')
    def api_build():
        return {
            'title': engine.title,
            'version': engine.version,
            'git_hash': engine.git_hash,
            'debug_hash': engine.debug_hash
        }

    @get('/vtt/api/logins')
    def api_query_logins():
        """Count users locations based on IPs within past 30d."""
        start = time.time()

        logins = engine.parse_login_log()
        locations = dict()
        platforms = dict()
        browsers = dict()
        since = start - 30 * 24 * 3600  # past 30d

        # group IPs by country
        for record in logins:
            if record.timeid < since:
                continue
            data = httpagentparser.detect(record.agent)

            # save data
            add_dict_set(locations, record.country, record.ip)
            if 'platform' in data:
                add_dict_set(platforms, data['platform']['name'], record.ip)
            else:
                add_dict_set(platforms, 'unknown', record.ip)
            if 'browser' in data:
                add_dict_set(browsers, data['browser']['name'], record.ip)
            else:
                add_dict_set(browsers, 'unknown', record.ip)

        # count IPs per country, platform and browser
        count_dict_set_len(locations)
        count_dict_set_len(platforms)
        count_dict_set_len(browsers)

        done = time.time()

        return {
            'locations': locations,
            'platforms': platforms,
            'browsers': browsers,
            'query_time': done - start
        }

    if engine.login['type'] == 'google':
        @get('/vtt/api/google')
        def api_query_google():
            # query gms and how many accounts do idle
            now = time.time()
            total = 0
            provider = {}
            for gm in engine.main_db.GM.select():
                # fetch provider
                p = '-'.join(gm.metadata.split('|')[:-1])
                for k in ['-oauth2', 'oauth2-']:
                    p = p.replace(k, '')
                if p not in provider:
                    provider[p] = 1
                else:
                    provider[p] += 1
            done = time.time()

            provider['query_time'] = done - now
            return provider
