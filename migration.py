#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import json, sys, os

from engine import Engine
from utils import PathApi


__author__ = 'Christian Glöckner'
__licence__ = 'MIT'


def rename_backup(fname):
    i = 1
    while True:
        target = str(fname) + '.{0}'.format(i)
        if os.path.exists(target):
            i += 1
        else:
            break
    os.rename(fname, target)


if __name__ == '__main__':
    if '--export' in sys.argv:
        # boot engine
        engine = Engine(argv=['--quiet'])
        print('{0} migration export started.'.format(engine.title))

        # export data to dict
        data = engine.saveToDict()

        # write data to json
        p = engine.paths.root / 'export.json'
        with open(p, 'w') as h:
            h.write(json.dumps(data, indent=4))
        
        print('Export finished.')

    else:
        # rename all databases to like gm.db.1 etc.
        print('Rename database files')
        paths = PathApi(appname='pyvtt')
        rename_backup(paths.getMainDatabasePath())
        for gmname in os.listdir(paths.getGmsPath()):
            fname = paths.getDatabasePath(gmname)
            rename_backup(fname)

        # boot engine (create tables etc.)  
        engine = Engine(argv=['--quiet'])
        print('{0} migration export started.'.format(engine.title))

        # load json from file 
        p = engine.paths.root / 'export.json'
        with open(p, 'r') as h:
            data = json.loads(h.read())

        # import data from dict
        engine.loadFromDict(data)
        
        print('Import finished.')

