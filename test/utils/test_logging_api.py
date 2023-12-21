"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import pathlib
import tempfile
import unittest

from vtt import utils


class LoggingApiTest(unittest.TestCase):
    
    def setUp(self):            
        # create temporary directory
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmpdir.name)
        
        self.logging = utils.LoggingApi(
            quiet=True,  # writing to sys.stdout not tested here
            info_file=self.root / 'info.log',
            error_file=self.root / 'error.log',
            access_file=self.root / 'access.log',
            warning_file=self.root / 'warning.log',
            logins_file=self.root / 'logins.log',
            auth_file=self.root / 'auth.log'
        )
        
    def tearDown(self):
        del self.logging
        del self.tmpdir
        
    def assert_last_line(self, log_name: str, line: str) -> None:
        with open(self.root / f'{log_name}.log', 'r') as h:
            content = h.read()
        last_line = content.split('\n')[-2]  # note: last line is empty
        self.assertTrue(last_line.endswith(line))  # ignore line's beginning (time etc.)

    def assert_file_not_found(self, log_name: str) -> None:
        with self.assertRaises(FileNotFoundError):
            with open(self.root / f'{log_name}.log', 'r') as _:
                pass
        
    def test_info(self):
        self.logging.info('hello info world')
        self.assert_last_line('info', 'hello info world')
        
    def test_error(self):
        self.logging.error('hello error world')
        self.assert_last_line('error', 'hello error world')
        
    def test_access(self):
        self.logging.access('hello access world')
        self.assert_last_line('access', 'hello access world')
        
    def test_warning(self):
        self.logging.warning('hello warning world')
        self.assert_last_line('warning', 'hello warning world')
        
    def test_logins(self):           
        data = {'id': '123', 'username': 'foobar'}
        self.logging.logins(data)
        self.assert_last_line('logins', str(data))
    
    def test_auth(self):              
        self.logging.auth('hello stats world')

    def test_stdout_only(self):
        # NOTE: manual setUp to make sure logs are cleared
        
        # create temporary directory
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmpdir.name)
        
        self.logging = utils.LoggingApi(
            quiet=False,
            info_file=self.root / 'info.log',
            error_file=self.root / 'error.log',
            access_file=self.root / 'access.log',
            warning_file=self.root / 'warning.log',
            logins_file=self.root / 'logins.log',
            auth_file=self.root / 'auth.log',
            stdout_only=True
        )

        # regular logs are empty
        self.logging.info('hello info world')
        self.assert_file_not_found('info')
         
        self.logging.error('hello error world')
        self.assert_file_not_found('error')
        
        self.logging.access('hello access world')
        self.assert_file_not_found('access')
        
        self.logging.warning('hello warning world')
        self.assert_file_not_found('warning')

        self.logging.auth('hello stats world')
        self.assert_file_not_found('auth')
        
        # stats log is not empty due to analysis stuff
        data = {'id': '123', 'username': 'foobar'}
        self.logging.logins(data)
        self.assert_last_line('logins', str(data))
