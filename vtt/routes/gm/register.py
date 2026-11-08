"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

import typing

from . import login, importer, drawer, scenes


def register(engine: typing.Any):
    login.register(engine)
    importer.register(engine)
    drawer.register(engine)
    scenes.register(engine)
