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


class BuildNumber(object):

    def __init__(self):
        self.version = [0, 0, 1]

    def __str__(self):
        return '{0}.{1}.{2}'.format(*self.version)

    def loadFromFile(self, fname):
        """ Load version number from single-line javascript file. """
        with open(fname, 'r') as h:
            line = h.read()
        version = line.split('"')[1].split('.')
        for i in [0, 1, 2]:
            version[i] = int(version[i])
        
        self.version = version

    def saveToFile(self, fname):
        """ Rewrite javascript file for new version number. """
        raw = 'const version = "{0}";'.format(self)
        with open(fname, 'w') as h:
            h.write(raw)

    def inc(self, k):
        self.version[k] += 1
        for i in range(k+1, len(self.version)):
            self.version[i] = 0

    def major(self):
        self.inc(0)

    def minor(self):
        self.inc(1)

    def fix(self):
        self.inc(2)


if __name__ == '__main__':
    path = pathlib.Path('static') / 'version.js'
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

