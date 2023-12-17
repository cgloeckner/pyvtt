"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import tempfile
import unittest
import pathlib

from vtt import utils


class ConstantExportTest(unittest.TestCase):
    
    def setUp(self):            
        # create temporary directory
        self.tmp_file = tempfile.NamedTemporaryFile()
        
    def tearDown(self):
        del self.tmp_file

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

        dumped = e.save_to_memory()
        expected = ('var test = "foo";\n'
                    'var bar = 42;\n'
                    'var number = 3.14;\n'
                    'var thing = true;\n'
                    'var other = false;\n')
        self.assertEqual(dumped, expected)

    def test_saveToFile(self):
        e = utils.ConstantExport()
        e['test'] = 'foo'
        e['bar'] = 42
        e['number'] = 3.14     
        e['thing'] = True
        e['other'] = False

        e.save_to_file(pathlib.Path(self.tmp_file.name))

        expected = ('/** DO NOT MODIFY THIS FILE. IT WAS CREATED AUTOMATICALLY. */'
                    '\n') + e.save_to_memory()
        with open(self.tmp_file.name, 'r') as h:
            content = h.read()
        self.assertEqual(content, expected)
