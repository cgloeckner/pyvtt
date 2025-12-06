"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

import random
import time

from pony.orm import Database


def create_roll(db: Database, game: 'Game', name: str, color: str, sides: int) -> 'Roll':
    return db.Roll(
        game=game,
        name=name,
        color=color,
        sides=sides,
        result=random.randrange(1, sides + 1),
        timeid=time.time()
    )
