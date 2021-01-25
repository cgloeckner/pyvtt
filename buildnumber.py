#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import pathlib, os, sys

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'


def loadVersion(fname):
    """ Load version number from single-line javascript file. """
    with open(fname, 'r') as h:
        line = h.read()
    version = line.split('"')[1].split('.')
    for i in [0, 1, 2]:
        version[i] = int(version[i])
    return version

def saveVersion(version, fname):
    """ Rewrite javascript file for new version number. """
    raw = 'const version = "{0}.{1}.{2}";'.format(*version)
    with open(fname, 'w') as h:
        h.write(raw)

if __name__ == '__main__':
    path    = pathlib.Path('static') / 'version.js'
    version = [0, 0, 0]
    if os.path.exists(path):
        version = loadVersion(path)
    print('Current version is {0}'.format(version))
    
    if '--major' in sys.argv:
        # increase major number
        version[0] += 1
        version[1] = 0
        version[2] = 0     
        saveVersion(version, path)
        print('New version is {0}'.format(version))
    elif '--minor' in sys.argv:
        # increase minor number
        version[1] += 1
        version[2] = 0    
        saveVersion(version, path)
        print('New version is {0}'.format(version))
    elif '--fix' in sys.argv:
        # increase fix number
        version[2] += 1   
        saveVersion(version, path)
        print('New version is {0}'.format(version))
    else:
        print('Arguments: Use "--major", "--minor" or "--fix" to increase version number')

