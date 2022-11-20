#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2022 Christian Glöckner
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
            logins_file  = self.root / 'logins.log',
            auth_file    = self.root / 'auth.log'
        )
        
    def tearDown(self):
        del self.logging
        del self.tmpdir
        
    def assertLastLine(self, logname, line):
        with open(self.root / '{0}.log'.format(logname), 'r') as h:
            content = h.read()
        last_line = content.split('\n')[-2] # note: last line is empty
        self.assertTrue(last_line.endswith(line)) # ignore line's beginning (time etc.)

    def assertFileNotFound(self, logname):
        with self.assertRaises(FileNotFoundError):
            with open(self.root / f'{logname}.log', 'r') as h:
                pass
        
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
        
    def test_logins(self):           
        data = {'id': '123', 'username': 'foobar'}
        self.logging.logins(data)
        self.assertLastLine('logins', str(data))
    
    def test_auth(self):              
        self.logging.auth('hello stats world')

    def test_stdout_only(self):
        # NOTE: manual setUp to make sure logs are cleared
        
        # create temporary directory
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root   = pathlib.Path(self.tmpdir.name)
        
        self.logging = utils.LoggingApi(
            quiet        = False,
            info_file    = self.root / 'info.log',
            error_file   = self.root / 'error.log',
            access_file  = self.root / 'access.log',
            warning_file = self.root / 'warning.log',
            logins_file  = self.root / 'logins.log',
            auth_file    = self.root / 'auth.log',
            stdout_only  = True
        )

        # regular logs are empty
        self.logging.info('hello info world')
        self.assertFileNotFound('info')
         
        self.logging.error('hello error world')
        self.assertFileNotFound('error')
        
        self.logging.access('hello access world')
        self.assertFileNotFound('access')
        
        self.logging.warning('hello warning world')
        self.assertFileNotFound('warning')

        self.logging.auth('hello stats world')
        self.assertFileNotFound('auth')
        
        # stats log is not empty due to analysis stuff
        data = {'id': '123', 'username': 'foobar'}
        self.logging.logins(data)
        self.assertLastLine('logins', str(data))


