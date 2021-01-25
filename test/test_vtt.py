#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import vtt

from test.utils import EngineBaseTest


class VttTest(EngineBaseTest):

    def setUp(self):
        super().setUp()
        vtt.setup_gm_routes(self.engine)
        vtt.setup_player_routes(self.engine)
        # @NOTE: custom errorpages are not routed here
    
    def test_get_root(self):
        # expect redirect to login
        ret = self.app.get('/')
        self.assertEqual(ret.status_int, 302)
        self.assertEqual(ret.location, 'http://localhost:80/vtt/join')

        # expect games menu if logged in
        ret = self.app.post('/vtt/join', {'gmname': 'arthur'})
        self.assertEqual(ret.status_int, 200)
        ret = self.app.get('/')
        self.assertEqual(ret.status_int, 200)

        # expect redirect if a session ID is faked
        self.app.set_cookie('session', 'randomstuffthatisnotasessionid')
        ret = self.app.get('/')
        self.assertEqual(ret.status_int, 302)
        self.assertEqual(self.app.cookies['session'], '""')

    def test_get_vtt_patreon_callback(self):
        # expect 404 because engine is loaded without patreon support
        # hence callback is not used in that case
        ret = self.app.get('/vtt/patreon/callback', expect_errors=True)
        self.assertEqual(ret.status_int, 404)
    
    def test_get_vtt_join(self):
        ret = self.app.get('/vtt/join')
        self.assertEqual(ret.status_int, 200)

    def test_post_vtt_join(self):
        # @NOTE: this route is working because the engine was loaded
        # without patreon-support, hence GMs can create an account
        # directly

        # can create a GM account
        args = {
            'gmname' : 'arthur'
        }
        ret = self.app.post('/vtt/join', args)
        self.assertEqual(ret.status_int, 200)
        # expect json response
        self.assertEqual(ret.json['error'], '')
        self.assertEqual(ret.json['url'], args['gmname'])
        self.assertIn('session', self.app.cookies)
        
        # cannot create GM with name collision             
        self.app.reset()
        ret = self.app.post('/vtt/join', args)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.json['error'], 'ALREADY IN USE')
        self.assertIsNone(ret.json['url'])
        self.assertNotIn('session', self.app.cookies)
        
        # can create GM but name is cut
        self.app.reset()
        args = {
            'gmname' : 'arthurhasaverylongnamethatiscutafter20chars'
        } 
        ret = self.app.post('/vtt/join', args)
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.json['error'], '')
        self.assertEqual(ret.json['url'], args['gmname'][:20])
        self.assertIn('session', self.app.cookies)

        # cannot create GM with invalid name   
        self.app.reset()
        ret = self.app.post('/vtt/join', {'gmname': 'king arthur'})
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.json['error'], 'NO SPECIAL CHARS OR SPACES')
        self.assertIsNone(ret.json['url'])
        self.assertNotIn('session', self.app.cookies)

        # cannot create GM with blacklisted name        
        self.app.reset()
        ret = self.app.post('/vtt/join', {'gmname': 'vtt'})
        self.assertEqual(ret.status_int, 200)
        self.assertEqual(ret.json['error'], 'RESERVED NAME')
        self.assertEqual(ret.json['url'], None)
        self.assertNotIn('session', self.app.cookies)

    # @NOTE: next is /vtt/fancy-url on line 197
