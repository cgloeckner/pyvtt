#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import unittest, tempfile, pathlib

import utils

class FancyUrlApiTest(unittest.TestCase):
    
    def setUp(self):            
        # create temporary directory
        self.tmpdir = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.tmpdir.name)
        
        self.paths = utils.PathApi(appname='unittest', root=root)
        self.urls = utils.FancyUrlApi(self.paths)
        
    def tearDown(self):
        del self.urls
        del self.paths
        del self.tmpdir
        
    def test___call__(self):
        urls = list()
        for i in range(100):
            url = self.urls()
            parts = url.split('-')
            self.assertEqual(len(parts), 3)
            urls.append(url)
        # expect multiple URLs (assumed to many of them but extreme collisions may happen, so at least 2)
        self.assertGreaterEqual(len(urls), 2)
