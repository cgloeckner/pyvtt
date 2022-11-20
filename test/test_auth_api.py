#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2022 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import unittest, tempfile, pathlib, os

import utils

class AuthApiTest(unittest.TestCase):
    
    def setUp(self):            
        pass
        
    def tearDown(self):
        pass
    
    def test_parseStateFromUrl(self):
        url = 'https://example.com/?foo=bar&state=deadbeef&more=stuff'
        state = utils.BaseLoginApi.parseStateFromUrl(url)

        self.assertEqual(state, 'deadbeef')

