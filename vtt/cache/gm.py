"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2022 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

import time

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

        self.engine = engine
        self.lock = lock.RLock()
        self.url = gm.url
        self.games = dict()
        self.db = None  # needs connect_db to be run (but outside a db_session)
        if self.engine.single_db_mode:
            self.engine.logging.info(f'Linking database for "{gm.name}" to global database')
            self.db = self.engine.main_db

    def connect_db(self):
        # connect to GM's database
        db_path = self.engine.paths.get_database_path(self.url)
        self.db = create_gm_database(self.engine, str(db_path))
        
        # add all existing games to the cache
        with db_session:
            for game in self.db.Game.select():
                self.insert(game)
                # reorder scenes by ID if necessary
                if game.order == list():
                    game.reorder_scenes()

    def create_game(self, url: str) -> 'Game':
        game = self.db.Game(
            url=url,
            timeid=time.time(),
            gm_url=self.url
        )
        game.post_setup()
        return game

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
