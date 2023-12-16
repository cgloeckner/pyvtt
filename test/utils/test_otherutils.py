#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2022 Christian Glöckner
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
        
        utils.addDictSet(d, 'foo', 'bar')
        self.assertIn('bar', d['foo'])
        
        utils.addDictSet(d, 'foo', 'bar')
        self.assertIn('bar', d['foo'])
        
        utils.addDictSet(d, 'foo', 'test')
        self.assertIn('bar', d['foo'])
        self.assertIn('test', d['foo'])

    def test_countDictSetLen(self):
        d = dict()
        d['test'] = set()
        utils.addDictSet(d, 'foo', 'bar')
        utils.addDictSet(d, 'foo', 'test')
        utils.addDictSet(d, 'bar', 'test')

        utils.countDictSetLen(d)
        self.assertEqual(d['test'], 0)
        self.assertEqual(d['foo'], 2)
        self.assertEqual(d['bar'], 1)
