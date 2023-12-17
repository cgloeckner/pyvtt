"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

import pathlib


class BuildNumber:

    def __init__(self) -> None:
        self.version = [0, 0, 1]

    def __str__(self) -> str:
        return '{0}.{1}.{2}'.format(*self.version)

    def load_from_file(self, path: pathlib.Path) -> None:
        """ Load version number from single-line javascript file. """
        with open(path, 'r') as h:
            line = h.read()
        version = line.split('"')[1].split('.')
        self.version = [int(num) for num in version]

    def save_to_file(self, path: pathlib.Path) -> None:
        """ Rewrite javascript file for new version number. """
        raw = 'const version = "{0}";'.format(self)
        with open(path, 'w') as h:
            h.write(raw)

    def inc(self, category: int) -> None:
        self.version[category] += 1

        # set sub-categories to 0
        for sub_category in range(category+1, len(self.version)):
            self.version[sub_category] = 0

    def major(self) -> None:
        self.inc(0)

    def minor(self) -> None:
        self.inc(1)

    def fix(self) -> None:
        self.inc(2)
