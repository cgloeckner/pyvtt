"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2022 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

import json

from gevent import lock

from vtt.orm.register import db_session
from .gm import GmCache


class EngineCache:
    """ Thread-safe gms dict using gm-url as key. """

    def __init__(self, engine: any) -> None:
        self.engine = engine
        self.lock = lock.RLock()
        self.gms = dict()

        # add all GMs from database
        with db_session:
            gms = self.engine.main_db.GM.select()
            for i, gm in enumerate(gms):
                self.engine.logging.info('Creating GM {0}/{1} #{2}'.format(i + 1, len(gms), gm.url))
                self.insert(gm)

        # initialize GMs databases
        for i, gm in enumerate(self.gms):
            self.gms[gm].connect_db()
            self.engine.logging.info('Loaded GM {0}/{1} #{2}'.format(i + 1, len(self.gms), gm))

        self.engine.logging.info('EngineCache created')

    # --- cache implementation ----------------------------------------

    def insert(self, gm):
        url = gm.url
        with self.lock:
            # @NOTE: existing GmCache is replaced
            # (e.g. relogin by user)
            self.gms[url] = GmCache(self.engine, gm)
            return self.gms[url]

    def get(self, gm):
        if gm:
            return self.get_from_url(gm.url)

    def get_from_url(self, url):
        with self.lock:
            try:
                return self.gms[url]
            except KeyError:
                return None

    def remove(self, gm):
        with self.lock:
            del self.gms[gm.url]

    # --- websocket implementation ------------------------------------

    def listen(self, socket):
        """ Handle new connection. """
        # read name and color
        raw = socket.receive()
        if raw is None:
            return
        data = json.loads(raw)
        name = data['name']
        gm_url = data['gm_url']
        game_url = data['game_url']

        # insert player
        gm_cache = self.get_from_url(gm_url)
        if gm_cache is None:
            self.engine.logging.warning('Cannot listen to websocket for GM {0}'.format(gm_url))
            return
        game_cache = gm_cache.get_from_url(game_url)
        if game_cache is None:
            self.engine.logging.warning('Cannot listen to websocket for game {0}'.format(game_url))
            return
        player_cache = game_cache.get(name)
        if player_cache is None:
            self.engine.logging.warning('Cannot listen to websocket as player {0}'.format(name))
            return

        # with player_cache.lock: # note: atm deadlocking
        player_cache.socket = socket
        game_cache.login(player_cache)

        # handle incomming data
        # NOTE: needs to be done async, else db_session will block,
        # because the route, which calls this listen() has its own
        # db_session due to the bottle configuration
        player_cache.handle_async()

        return player_cache



