#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import json, sys, os

from engine import Engine
from vtt.utils.common import PathApi


__author__ = 'Christian Glöckner'
__licence__ = 'MIT'


def rename_backup(fname):
    if not os.path.exists(fname):
        return
    
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

    elif '--import' in sys.argv:
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

    elif '--music' in sys.argv:
        # rename each games' "music.mp3" to "0.mp3"
        print('Rename music files')
        paths = PathApi(appname='pyvtt')
        n = 0
        for gmname in os.listdir(paths.getGmsPath()):
            gm_root = paths.getGmsPath(gmname)
            for gameurl in os.listdir(gm_root):
                if not os.path.isdir(gm_root / gameurl):
                    continue
                # check for file to rename
                old_fname = paths.getGamePath(gmname, gameurl) / 'music.mp3'
                new_fname = paths.getGamePath(gmname, gameurl) / '0.mp3'
                if os.path.exists(old_fname):
                    os.rename(old_fname, new_fname)
                    n += 1
        print('{0} Music Files Renamed. Migration finished.'.format(n))

    else:
        print('Nothing specified.')
