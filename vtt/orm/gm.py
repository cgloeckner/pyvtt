"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

import base64
import os
import shutil
import time
import uuid
import typing

import bottle
from gevent import lock
from pony.orm import *


CleanupReport = tuple[list[str], int, int, int, int]


class BaseGm(typing.Protocol):
    def post_setup(self) -> None: ...
    def has_expired(self, now: int) -> bool: ...
    @staticmethod
    def cleanup(gm_db: Database, now: int) -> CleanupReport: ...
    def pre_delete(self) -> int: ...
    def refresh_session(self, response: bottle.Response) -> None: ...
    @staticmethod
    def load_from_session(request: bottle.Request) -> 'BaseGm': ...
    @staticmethod
    def generate_session() -> str: ...
    @staticmethod
    def generate_uuid() -> str: ...


def register(engine: any, db: Database):

    class GM(db.Entity):
        id = PrimaryKey(int, auto=True)
        name = Required(str)
        url = Required(str, unique=True)
        sid = Required(str, unique=True)
        identity = Required(str, unique=True)
        metadata = Optional(str)
        timeid = Optional(float)  # used for cleanup

        def post_setup(self) -> None:
            self.timeid = int(time.time())

            engine.storage.setup_gm(self.url)

            # add to engine's GM cache
            engine.cache.insert(self)

        def has_expired(self, now: int, gm_db: Database) -> bool:
            delta = now - self.timeid
            if self.timeid == 0 or delta <= engine.cleanup['expire']:
                return False

            # check whether all games have expired too
            for game in gm_db.Game.select(gm_url=self.url):
                if not game.has_expired(now, 1.0):
                    # at least this game did not expire yet
                    return False

            return True

        @staticmethod
        def cleanup(gm_db: Database, now: int) -> CleanupReport:
            """ Cleanup GM's games' outdated rolls, unused images or
            event remove expired games (see engine.cleanup['expire']).
            """
            games = list()
            num_bytes = 0
            num_rolls = 0
            num_tokens = 0
            num_md5s = 0

            for g in gm_db.Game.select():
                if g.has_expired(now):
                    # remove this game
                    num_bytes += g.pre_delete()
                    games.append(f'{g.gm_url}/{g.url}')
                    g.delete()
                    continue

                # cleanup this game
                b, r, t, m = g.cleanup(now)
                num_bytes += b
                num_rolls += r
                num_tokens += t
                num_md5s += m

            return games, num_bytes, num_rolls, num_tokens, num_md5s

        def pre_delete(self) -> int:
            """ Remove this GM from disk to allow removing him from
            the main database.
            """
            engine.logging.info('Removing GM {0} <{1}>'.format(self.name, self.url))

            # remove GM's directory (including his database, all games and images)
            root_path = engine.paths.get_gms_path(self.url)
            num_bytes = os.path.getsize(root_path)

            with engine.storage.locks[self.url]:  # make IO access safe
                shutil.rmtree(root_path)

            # remove GM from engine's cache
            engine.cache.remove(self)

            return num_bytes

        def refresh_session(self, response: bottle.Response) -> None:
            """ Refresh session id. """
            now = time.time()
            self.timeid = now
            response.set_cookie('session', self.sid, path='/', expires=now + engine.cleanup['expire'])

        @staticmethod
        def load_from_session(request: bottle.Request) -> 'GM':
            """ Fetch GM from session id and ip address. """
            sid = request.get_cookie('session')
            return GM.select(lambda g: g.sid == sid).first()

        @staticmethod
        def generate_session() -> str:
            return uuid.uuid4().hex

        @staticmethod
        def generate_uuid() -> str:
            u = uuid.uuid4()
            return base64.urlsafe_b64encode(u.bytes).decode("utf-8").strip('=')

    return GM
