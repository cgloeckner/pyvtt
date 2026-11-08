"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

import time
import typing

from pony.orm import *

from .protocols import TokenLike


def register(_: typing.Any, db: Database):

    Token = db.entities["Token"]

    class Scene(db.Entity):
        id = PrimaryKey(int, auto=True)
        game = Required("Game")
        tokens = Set("Token", cascade_delete=True, reverse="scene")  # forward deletion to tokens
        backing = Optional("Token", reverse="back")  # background token

        def create_token(self, **kwargs) -> TokenLike:
            if 'timeid' not in kwargs:
                kwargs['timeid'] = time.time()

            return Token(scene=self, **kwargs)

        def pre_delete(self):
            # delete all tokens
            for t in self.tokens:
                t.delete()
            self.backing = None

    return Scene
