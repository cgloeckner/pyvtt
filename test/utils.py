#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import unittest, webtest, sys, tempfile, pathlib, json, time

import bottle
from geventwebsocket.exceptions import WebSocketError

from utils import PathApi
from engine import Engine

class EngineBaseTest(unittest.TestCase):
        
    def setUp(self):
        # create temporary directory
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root   = pathlib.Path(self.tmpdir.name)
        
        # pregenerate paths api for dummyfiles            
        paths = PathApi(appname='unittest', root=self.root)
        for w in ['verbs', 'adjectives', 'nouns']:
            with open(paths.getFancyUrlPath() / '{0}.txt'.format(w), 'w') as h:
                h.write('demo')
        
        # load engine app into webtest
        self.engine = Engine(argv=['--quiet'], pref_dir=self.root)
        self.engine.app.catchall = False
        self.app = webtest.TestApp(self.engine.app)
        
        self.monkeyPatch()
        
    def monkeyPatch(self):
        # save methods for later
        self.prev_getPublicIp = self.engine.getPublicIp
        self.prev_getCountryFromIp = self.engine.getCountryFromIp
        # monkey-patch methods with stubs
        self.engine.getPublicIp = lambda: '?.?.?.?'
        self.engine.getCountryFromIp = lambda ip: 'unknown'
        
    def tearDown(self):
        # unload engine
        del self.app
        del self.engine
        del self.tmpdir


# ---------------------------------------------------------------------

class SocketDummy(object):
    """ Dummy class for working with a socket.
    """
    
    def __init__(self):
        self.clearAll()
        
    def clearAll(self):
        self.read_buffer  = list()
        self.write_buffer = list()
        
        self.closed = False
        self.block  = True
        
    def receive(self):
        if self.closed:
            raise WebSocketError('SocketDummy is closed')
        # block if buffer empty
        while self.block and len(self.read_buffer) == 0:
            time.sleep(0.01)
        # yield buffer element
        if len(self.read_buffer) > 0:
            return self.read_buffer.pop(0)
        return None
        
    def push_receive(self, data):
        self.read_buffer.append(json.dumps(data))
        
    def send(self, s):
        if self.closed:
            raise WebSocketError('SocketDummy is closed')
        self.write_buffer.append(s)
        
    def pop_send(self):
        if len(self.write_buffer) > 0:
            return json.loads(self.write_buffer.pop(0))
        return None
        
    def close(self):
        if self.closed:
            raise WebSocketError('SocketDummy is closed')
        self.closed = True


# ---------------------------------------------------------------------

def presetup_unittest(argv):
    argv.append('--quiet')
    argv.append('--debug')
    argv.append('--localhost')
    return argv


def setup_unittest_routes(engine):
    @bottle.get('/vtt/unittest/game')
    @bottle.view('unittest_game')
    def unittest_demo_game():
        gm = engine.main_db.GM.select(lambda gm: gm.url == 'arthur').first()
        gm_cache = engine.cache.getFromUrl('arthur')
        game = gm_cache.db.Game.select(lambda g: g.url == 'test-game-1').first()
            
        websocket_url = engine.getWebsocketUrl()
            
        return dict(engine=engine, user_agent='UNITTEST', websocket_url=websocket_url, game=game, playername='arthur',playercolor='#FF0000', gm=gm, is_gm=True)

    # setup demo game
    # @TODO register GM arthur
    # @TODO create game test-game-1 with background "/static/background.jpg"
    
    server_uri = engine.getUrl()
    print('=' * 80)
    print('URLs for Unittest scenarios:')
    for route in ['/vtt/unittest/game']:
        print('\t{0}{1}'.format(server_uri, route))
    print('=' * 80)

