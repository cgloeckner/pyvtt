"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

import math

from pony.orm import *

from .constants import *


def register(_, db):

    class Token(db.Entity):
        id = PrimaryKey(int, auto=True)
        scene = Required("Scene")
        url = Required(str)
        posx = Required(int)
        posy = Required(int)
        zorder = Required(int, default=0)
        size = Required(int)
        rotate = Required(float, default=0.0)
        flipx = Required(bool, default=False)
        locked = Required(bool, default=False)
        timeid = Required(float, default=0.0)  # dirty flag
        back = Optional("Scene")  # link to same scene as above but may be None
        text = Optional(str)  # text
        color = Optional(str)  # used for label

        def update(self, timeid: float, pos: tuple[int, int] | None = None, zorder: int | None = None,
                   size: int | None = None, rotate: float | None = None, flipx: bool | None = None,
                   locked: bool | None = None, text: str | None = None):
            """Handle update of several data fields. The time-id is set if anything
            has actually changed.
            """
            updated = False

            if self.locked and locked is None:
                # token is locked and not unlocked
                return updated

            if locked is not None and self.locked != locked:
                self.timeid = timeid
                self.locked = locked
                updated = True

            if pos is not None:
                # force position onto scene (canvas)
                self.posx = min(MAX_SCENE_WIDTH, max(0, pos[0]))
                self.posy = min(MAX_SCENE_HEIGHT, max(0, pos[1]))
                self.timeid = timeid
                updated = True

            if zorder is not None:
                self.zorder = zorder
                self.timeid = timeid
                updated = True

            if size is not None:
                self.size = min(MAX_TOKEN_SIZE, max(MIN_TOKEN_SIZE, size))
                self.timeid = timeid
                updated = True

            if rotate is not None:
                self.rotate = rotate
                self.timeid = timeid
                updated = True

            if flipx is not None:
                self.flipx = flipx
                self.timeid = timeid
                updated = True

            if text is not None:
                self.text = text[0][:MAX_TOKEN_LABEL_SIZE]
                self.color = text[1]
                self.timeid = timeid
                updated = True

            return updated

        @staticmethod
        def get_pos_by_degree(origin: tuple[int, int], k: int, n: int) -> tuple[int, int]:
            """ Get Position in circle around origin of the k-th item of n. """
            # determine degree and radius
            degree = k * 360 / n
            radius = 32 * n ** 0.5
            if n == 1:
                radius = 0

            # calculate position in unit circle
            s = math.sin(degree * 3.14 / 180)
            c = math.cos(degree * 3.14 / 180)

            # calculate actual position
            x = int(origin[0] - radius * s)
            y = int(origin[1] + radius * c)

            # force position onto scene (canvas)
            x = min(MAX_SCENE_WIDTH, max(0, x))
            y = min(MAX_SCENE_HEIGHT, max(0, y))

            return x, y

    return Token