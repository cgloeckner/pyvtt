"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import pathlib
import sys
import tempfile
import unittest
import pytest

from vtt import utils


class PathApiTest(unittest.TestCase):
    
    def setUp(self):            
        # create temporary directory
        self.tmpdir = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.tmpdir.name)
        
        self.paths = utils.PathApi(appname='unittest', pref_root=root)

    def tearDown(self):
        del self.paths
        del self.tmpdir
        
    def assert_directory(self, p: pathlib.Path) -> None:
        self.assertTrue(p.exists())

    def test_path_api_with_given_prefroot(self):
        # as setUp
        expected = pathlib.Path(self.tmpdir.name) / 'unittest'
        self.assertEqual(self.paths.pref_root, expected)
        
    def test_path_api_without_specific_prefroot(self):
        paths = utils.PathApi(appname='unittest')
        expected = pathlib.Path.cwd() / 'data' / 'unittest'
        self.assertEqual(paths.pref_root, expected)

    def test_ensure(self):
        # @NOTE: ensure() is called by the constructor
        
        # test required paths
        self.assert_directory(self.paths.pref_root)
        self.assert_directory(self.paths.get_export_path())
        self.assert_directory(self.paths.get_gms_path())
        self.assert_directory(self.paths.get_fancy_url_path())
        self.assert_directory(self.paths.get_static_path())
        self.assert_directory(self.paths.get_assets_path())
        self.assert_directory(self.paths.get_client_code_path())
        
    def test_simple_path_getter(self):
        # @NOTE: actual value isn't tested but that they are not throwing
        self.paths.get_static_path()
        self.paths.get_static_path(default=True)
        self.paths.get_assets_path()
        self.paths.get_assets_path(default=True)
        self.paths.get_client_code_path()
        #self.paths.get_settings_path()
        self.paths.get_main_database_path()
        self.paths.get_constants_path()
        self.paths.get_ssl_path()
        self.paths.get_log_path('foo')
        
    def test_advanced_path_getter(self):
        # test GM(s) Path(s)
        gms_root = self.paths.get_gms_path()
        self.assertEqual(gms_root.parts[-1], 'gms')
        single_path = self.paths.get_gms_path('foo')
        self.assertEqual(single_path.parts[-1], 'foo')
        
        # test fancy url paths
        fancy_root = self.paths.get_fancy_url_path()
        self.assertEqual(fancy_root.parts[-1], 'fancyurl')
        txt_file = self.paths.get_fancy_url_path('bar')
        self.assertEqual(txt_file.parts[-1], 'bar.txt')
        
        # test database paths
        db_path = self.paths.get_database_path('foo')
        self.assertEqual(db_path.parts[-2], 'foo')
        self.assertEqual(db_path.parts[-1], 'gm.db')

        # test md5 json paths
        md5_path = self.paths.get_md5_path('foo', 'bar')
        self.assertEqual(md5_path.parts[-3], 'foo')
        self.assertEqual(md5_path.parts[-2], 'bar')
        self.assertEqual(md5_path.parts[-1], 'gm.md5')
        
        # test game paths
        game_path = self.paths.get_game_path('foo', 'bar')
        self.assertEqual(game_path.parts[-2], 'foo')
        self.assertEqual(game_path.parts[-1], 'bar')
        
        
