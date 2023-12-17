"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2022 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

from gevent import lock

from vtt.orm.register import db_session, create_gm_database
from .game import GameCache


class GmCache:
    """ Thread-safe GM dict using game-url as key.
    Holds GM-databases.
    """

    def __init__(self, engine: any, gm: any) -> None:
        # ensure engine can lock for this GM if required
        gm.make_lock()
        self.db_path = engine.paths.get_database_path(gm.url)

        self.engine = engine
        self.lock = lock.RLock()
        self.url = gm.url
        self.games = dict()
        self.db = None  # needs connect_db to be run (but outside a db_session)

        # self.engine.logging.info('GmCache {0} with {0} created'.format(self.url, self.db_path))

    def connect_db(self):
        # connect to GM's database
        self.db = create_gm_database(self.engine, str(self.db_path))

        # add all existing games to the cache
        with db_session:
            for game in self.db.Game.select():
                self.insert(game)
                # reorder scenes by ID if necessary
                if game.order == list():
                    game.reorder_scenes()

        # self.engine.logging.info('GmCache {0} with {0} loaded'.format(self.url, self.db_path))

    # --- cache implementation ----------------------------------------

    def insert(self, game):
        """ Try to insert a game into GM's Cache. """
        url = game.url
        with self.lock:
            if url in self.games:
                raise KeyError(url)
            self.games[url] = GameCache(self.engine, self, game)
            return self.games[url]

    def get(self, game: any) -> str:
        return self.get_from_url(game.url)

    def get_from_url(self, url: str) -> str | None:
        with self.lock:
            try:
                return self.games[url]
            except KeyError:
                return None

    def remove(self, game: any) -> None:
        with self.lock:
            del self.games[game.url]
