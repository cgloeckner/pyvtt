"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import unittest

from vtt import utils


class OtherTests(unittest.TestCase):
    
    def setUp(self):
        pass
        
    def tearDown(self):
        pass

    def test_addDictSet(self):
        d = dict()
        
        utils.add_dict_set(d, 'foo', 'bar')
        self.assertIn('bar', d['foo'])
        
        utils.add_dict_set(d, 'foo', 'bar')
        self.assertIn('bar', d['foo'])
        
        utils.add_dict_set(d, 'foo', 'test')
        self.assertIn('bar', d['foo'])
        self.assertIn('test', d['foo'])

    def test_countDictSetLen(self):
        d = dict()
        d['test'] = set()
        utils.add_dict_set(d, 'foo', 'bar')
        utils.add_dict_set(d, 'foo', 'test')
        utils.add_dict_set(d, 'bar', 'test')

        utils.count_dict_set_len(d)
        self.assertEqual(d['test'], 0)
        self.assertEqual(d['foo'], 2)
        self.assertEqual(d['bar'], 1)
