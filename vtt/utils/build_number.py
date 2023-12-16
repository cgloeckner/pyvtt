"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

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

