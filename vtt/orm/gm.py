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

from gevent import lock
from pony.orm import *


def register(engine, db):

    class GM(db.Entity):
        id = PrimaryKey(int, auto=True)
        name = Required(str)
        url = Required(str, unique=True)
        sid = Required(str, unique=True)
        identity = Required(str, unique=True)
        metadata = Optional(str)
        timeid = Optional(float)  # used for cleanup

        def makeLock(self):
            engine.locks[self.url] = lock.RLock()

        def postSetup(self):
            self.timeid = int(time.time())

            self.makeLock()

            root_path = engine.paths.getGmsPath(self.url)

            with engine.locks[self.url]:  # make IO access safe
                if not os.path.isdir(root_path):
                    os.mkdir(root_path)

            # add to engine's GM cache
            engine.cache.insert(self)

        def hasExpired(self, now):
            delta = now - self.timeid
            return self.timeid > 0 and delta > engine.cleanup['expire']

        def cleanup(self, gm_db, now):
            """ Cleanup GM's games' outdated rolls, unused images or
            event remove expired games (see engine.cleanup['expire']).
            """
            games = list()
            num_bytes = 0
            num_rolls = 0
            num_tokens = 0
            num_md5s = 0

            for g in gm_db.Game.select():
                if g.hasExpired(now):
                    # remove this game
                    num_bytes += g.preDelete()
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

        def preDelete(self):
            """ Remove this GM from disk to allow removing him from
            the main database.
            """
            engine.logging.info('Removing GM {0} <{1}>'.format(self.name, self.url))

            # remove GM's directory (including his database, all games and images)
            root_path = engine.paths.getGmsPath(self.url)
            num_bytes = os.path.getsize(root_path)

            with engine.locks[self.url]:  # make IO access safe
                shutil.rmtree(root_path)

            # remove GM from engine's cache
            engine.cache.remove(self)

            return num_bytes

        def refreshSession(self, response):
            """ Refresh session id. """
            now = time.time()
            self.timeid = now
            response.set_cookie('session', self.sid, path='/', expires=now + engine.cleanup['expire'])

        @staticmethod
        def loadFromSession(request):
            """ Fetch GM from session id and ip address. """
            sid = request.get_cookie('session')
            return db.GM.select(lambda g: g.sid == sid).first()

        @staticmethod
        def genSession():
            return uuid.uuid4().hex

        @staticmethod
        def genUUID():
            u = uuid.uuid4()
            return base64.urlsafe_b64encode(u.bytes).decode("utf-8").strip('=')

    return GM
