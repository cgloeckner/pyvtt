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


class ConstantExportTest(unittest.TestCase):
    
    def setUp(self):            
        # create temporary directory
        self.tmpfile = tempfile.NamedTemporaryFile()
        
    def tearDown(self):
        del self.tmpfile

    def test_setitem(self):
        e = utils.ConstantExport()
        self.assertEqual(len(e.data), 0)

        e['test'] = 'foo'
        e['bar'] = 42
        e['number'] = 3.14     
        e['thing'] = True
        e['other'] = False
        self.assertEqual(e.data['test'], 'foo')
        self.assertEqual(e.data['bar'], 42)
        self.assertEqual(e.data['number'], 3.14)
        self.assertTrue(e.data['thing'])
        self.assertFalse(e.data['other'])
        
    def test_saveToMemory(self):
        e = utils.ConstantExport()
        e['test'] = 'foo'
        e['bar'] = 42
        e['number'] = 3.14     
        e['thing'] = True
        e['other'] = False

        dumped = e.saveToMemory()
        expected = 'var test = "foo";\nvar bar = 42;\nvar number = 3.14;\nvar thing = true;\nvar other = false;\n'
        self.assertEqual(dumped, expected)

    def test_saveToFile(self):
        e = utils.ConstantExport()
        e['test'] = 'foo'
        e['bar'] = 42
        e['number'] = 3.14     
        e['thing'] = True
        e['other'] = False

        e.saveToFile(self.tmpfile.name)

        expected = '/** DO NOT MODIFY THIS FILE. IT WAS CREATED AUTOMATICALLY. */\n' + e.saveToMemory()
        with open(self.tmpfile.name, 'r') as h:
            content = h.read()
        self.assertEqual(content, expected)

        
        
