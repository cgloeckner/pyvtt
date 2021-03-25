#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import json, sys, pathlib

from engine import Engine


__author__ = 'Christian Glöckner'
__licence__ = 'MIT'


if __name__ == '__main__':
    if '--export' in sys.argv:
        engine = Engine(argv=['--quiet'])
        print('{0} migration export started.'.format(engine.title))

        # export data to dict
        data = engine.saveToDict()

        # write data to json
        p = engine.paths.root / 'export.json'
        with open(p, 'w') as h:
            h.write(json.dumps(data, indent=4))

    else:
        print('NOT IMPLEMENTED YET')

