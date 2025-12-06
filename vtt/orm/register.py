"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

from pony.orm import *

from . import token, scene, roll, game, gm


def register_gm_database(engine: any, db: Database) -> None:
    engine.orm['Token'] = token.register(engine, db)
    engine.orm['Scene'] = scene.register(engine, db)
    engine.orm['Roll'] = roll.register(engine, db)
    engine.orm['Game'] = game.register(engine, db)


def create_gm_database(engine: any, filename: str) -> Database:
    """ Creates a new database for with GM entities such as Tokens, Scenes etc."""
    if engine.single_db_mode:
        # use global db
        return engine.main_db
    
    # create custom db
    db = Database()
    register_gm_database(engine, db)

    # bind
    db.bind('sqlite', str(filename), create_db=True)
    db.generate_mapping(create_tables=True)
    return db


def create_main_database(engine: any) -> Database:
    """ Creates main database for GM data."""
    db = Database()

    # register entities
    engine.orm['GM'] = gm.register(engine, db)
    if engine.single_db_mode:
        register_gm_database(engine, db)

    # bind
    main_db_path = engine.paths.get_main_database_path()
    db.bind('sqlite', str(main_db_path), create_db=True)
    db.generate_mapping(create_tables=True)
    return db
