"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

from pony.orm import *

from . import token, scene, roll, game, gm


def createGmDatabase(engine, filename):
    """ Creates a new database for with GM entities such as Tokens, Scenes etc."""
    db = Database()

    token.register(engine, db)
    scene.register(engine, db)
    roll.register(engine, db)
    game.register(engine, db)

    db.bind('sqlite', filename, create_db=True)
    db.generate_mapping(create_tables=True)
    return db


def createMainDatabase(engine):
    """ Creates main database for GM data."""
    db = Database()

    gm.register(engine, db)

    db.bind('sqlite', str(engine.paths.get_main_database_path()), create_db=True)
    db.generate_mapping(create_tables=True)
    return db
