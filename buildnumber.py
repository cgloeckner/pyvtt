#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2022 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import pathlib, os, sys
  
from utils import BuildNumber


__author__ = 'Christian Glöckner'
__licence__ = 'MIT'


if __name__ == '__main__':
    path = pathlib.Path('static') / 'client' / 'version.js'
    version = BuildNumber()
    
    if os.path.exists(path):
        version.loadFromFile(path)
    print('Current version is {0}'.format(version))
    
    if '--major' in sys.argv:
        version.major()
    elif '--minor' in sys.argv:
        version.minor()
    elif '--fix' in sys.argv:
        version.fix()
    else:
        print('Arguments: Use "--major", "--minor" or "--fix" to increase version number')
        sys.exit(0)

    version.saveToFile(path)
    print('New version is {0}'.format(version))

