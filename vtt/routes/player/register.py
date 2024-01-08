"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

from . import login, play
from ..gm import thumbnail


def register(engine: any):
    login.register(engine)
    thumbnail.register(engine)
    play.register(engine)
