#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import unittest, tempfile, pathlib, os

import utils

class LoggingApiTest(unittest.TestCase):
    
    def setUp(self):            
        # create temporary directory
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root   = pathlib.Path(self.tmpdir.name)
        
        self.logging = utils.LoggingApi(
            quiet        = True, # writing to sys.stdout not tested here
            info_file    = self.root / 'info.log',
            error_file   = self.root / 'error.log',
            access_file  = self.root / 'access.log',
            warning_file = self.root / 'warning.log',
            stats_file   = self.root / 'stats.log'
        )
        
    def tearDown(self):
        del self.logging
        del self.tmpdir
        
    def assertLastLine(self, logname, line):
        with open(self.root / '{0}.log'.format(logname), 'r') as h:
            content = h.read()
        last_line = content.split('\n')[-2] # note: last line is empty
        self.assertTrue(last_line.endswith(line)) # ignore line's beginning (time etc.)
        
    def test_info(self):
        self.logging.info('hello info world')
        self.assertLastLine('info', 'hello info world')
        
    def test_error(self):
        self.logging.error('hello error world')
        self.assertLastLine('error', 'hello error world')
        
    def test_access(self):
        self.logging.access('hello access world')
        self.assertLastLine('access', 'hello access world')
        
    def test_warning(self):
        self.logging.warning('hello warning world')
        self.assertLastLine('warning', 'hello warning world')
        
    def test_stats(self):
        self.logging.stats('hello stats world')
        self.assertLastLine('stats', 'hello stats world')
