#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import unittest, tempfile, pathlib, os

import utils

class PathApiTest(unittest.TestCase):
    
    def setUp(self):            
        # create temporary directory
        self.tmpdir = tempfile.TemporaryDirectory()
        root        = pathlib.Path(self.tmpdir.name)
        
        self.paths = utils.PathApi(appname='unittest', root=root)
        
    def tearDown(self):
        del self.paths
        del self.tmpdir
        
    def assertDirectory(self, p):
        self.assertTrue(os.path.exists(p))
        
    def test_ensure(self):
        # @NOTE: ensure() is called by the constructpr
        
        # test required paths
        self.assertDirectory(self.paths.root)
        self.assertDirectory(self.paths.getExportPath()) 
        self.assertDirectory(self.paths.getGmsPath()) 
        self.assertDirectory(self.paths.getFancyUrlPath())
        self.assertDirectory(self.paths.getStaticPath())
        
    def test_simple_path_getter(self):
        # @NOTE: actual value isn't tested but that they are not throwing
        self.paths.getStaticPath()
        self.paths.getSettingsPath() 
        self.paths.getMainDatabasePath() 
        self.paths.getSslPath()
        self.paths.getLogPath('foo')

        self.assertEqual(self.paths.getMusicFileName(), 'music.mp3')
        
    def test_advanced_path_getter(self):
        # test GM(s) Path(s)
        gms_root = self.paths.getGmsPath()
        self.assertEqual(gms_root.parts[-1], 'gms')
        single_path = self.paths.getGmsPath('foo')
        self.assertEqual(single_path.parts[-1], 'foo')
        
        # test fancy url paths
        fancy_root = self.paths.getFancyUrlPath()
        self.assertEqual(fancy_root.parts[-1], 'fancyurl')
        txt_file = self.paths.getFancyUrlPath('bar')
        self.assertEqual(txt_file.parts[-1], 'bar.txt')
        
        # test database paths
        db_path = self.paths.getDatabasePath('foo') 
        self.assertEqual(db_path.parts[-2], 'foo')
        self.assertEqual(db_path.parts[-1], 'gm.db')

        # test md5 json paths
        md5_path = self.paths.getMd5Path('foo') 
        self.assertEqual(db_path.parts[-2], 'foo')
        self.assertEqual(db_path.parts[-1], 'gm.md5')
        
        # test game paths
        game_path = self.paths.getGamePath('foo', 'bar')
        self.assertEqual(game_path.parts[-2], 'foo')
        self.assertEqual(game_path.parts[-1], 'bar')
        
        
