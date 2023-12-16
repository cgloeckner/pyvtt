#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2022 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import tempfile
import unittest

from vtt import utils


class BuildNumberTest(unittest.TestCase):

    def setUp(self):
        self.file = tempfile.NamedTemporaryFile()

    def tearDown(self):
        pass

    def test_init(self):
        v = utils.BuildNumber()
        self.assertEqual(0, v.version[0])
        self.assertEqual(0, v.version[1])
        self.assertEqual(1, v.version[2])

    def test_str(self):
        v = utils.BuildNumber()
        v.version = ['a', 'b', 'c']
        s = '{0}'.format(v)
        self.assertEqual(s, 'a.b.c')

    def test_loadFromFile(self):
        # create js version file
        with open(self.file.name, 'w') as h:
            h.write('const version = "15.624.115";')

        v = utils.BuildNumber()
        v.loadFromFile(self.file.name)
        self.assertEqual(15, v.version[0])
        self.assertEqual(624, v.version[1])
        self.assertEqual(115, v.version[2])

    def test_saveToFile(self):
        v = utils.BuildNumber()
        v.version = [23, 73, 234]
        v.saveToFile(self.file.name)

        # load js version file
        with open(self.file.name, 'r') as h:
            c = h.read()
        self.assertEqual(c, 'const version = "23.73.234";')

    def test_major(self):
        v = utils.BuildNumber()
        v.version = [23, 73, 234]
        v.major()

        self.assertEqual(24, v.version[0])
        self.assertEqual(0, v.version[1])
        self.assertEqual(0, v.version[2])

    def test_minor(self):
        v = utils.BuildNumber()
        v.version = [23, 73, 234]
        v.minor()

        self.assertEqual(23, v.version[0])
        self.assertEqual(74, v.version[1])
        self.assertEqual(0, v.version[2])

    def test_fix(self):
        v = utils.BuildNumber()
        v.version = [23, 73, 234]
        v.fix()

        self.assertEqual(23, v.version[0])
        self.assertEqual(73, v.version[1])
        self.assertEqual(235, v.version[2])
