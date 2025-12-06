"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

import time

from pony.orm import *


def register(_: any, db: Database):

    class Scene(db.Entity):
        id = PrimaryKey(int, auto=True)
        game = Required("Game")
        tokens = Set("Token", cascade_delete=True, reverse="scene")  # forward deletion to tokens
        backing = Optional("Token", reverse="back")  # background token

        def create_token(self, **kwargs) -> 'Token':
            if 'timeid' not in kwargs:
                kwargs['timeid'] = time.time()

            return db.Token(scene=self, **kwargs)

        def pre_delete(self):
            # delete all tokens
            for t in self.tokens:
                t.delete()
            self.backing = None

    return Scene
