"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

from pony.orm import *

from . import token, scene, roll, game, gm


def create_gm_database(engine: any, filename: str) -> Database:
    """ Creates a new database for with GM entities such as Tokens, Scenes etc."""
    db = Database()

    token.register(engine, db)
    scene.register(engine, db)
    roll.register(engine, db)
    game.register(engine, db)

    db.bind('sqlite', filename, create_db=True)
    db.generate_mapping(create_tables=True)
    return db


def create_main_database(engine: any) -> Database:
    """ Creates main database for GM data."""
    db = Database()

    gm.register(engine, db)

    main_db_path = engine.paths.get_main_database_path()
    db.bind('sqlite', str(main_db_path), create_db=True)
    db.generate_mapping(create_tables=True)
    return db
