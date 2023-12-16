"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

from pony.orm import *


def register(_, db):

    class Roll(db.Entity):
        id = PrimaryKey(int, auto=True)
        game = Required("Game")
        name = Required(str)
        color = Required(str)
        sides = Required(int)
        result = Required(int)
        timeid = Required(float, default=0.0)

    return Roll
