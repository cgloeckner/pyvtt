#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

from test.utils import EngineBaseTest

class ExampleTest(EngineBaseTest):
    
    def test_landingpage(self):
        # expect redirect to login
        ret = self.app.get('/')
        self.assertEqual(ret.status_int, 302)
        self.assertEqual(ret.location, 'http://localhost:80/vtt/join')
