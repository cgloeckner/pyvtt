#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

import sys

from vtt.orm.register import db_session
from vtt import engine


# FIXME: deprecated implementation


if __name__ == '__main__':
    e = engine.Engine(sys.argv)

    gm_url   = sys.argv[1]
    game_url = sys.argv[2]

    gm_cache = e.cache.getFromUrl(gm_url)

    with db_session:
        game = gm_cache.db.Game.select(lambda g: g.url == game_url).first()

        zip_file, zip_path = game.toZip()

        print(gm_url, '/', game_url)
        print(zip_path / zip_file)
