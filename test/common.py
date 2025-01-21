"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2022 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import json
import pathlib
import tempfile
import time
import unittest
import zipfile
import os
import functools

import bottle
import webtest
from PIL import Image
from geventwebsocket.exceptions import WebSocketError

from vtt.engine import Engine
from vtt.cache import PlayerCache
from vtt.utils import PathApi


@functools.cache
def make_image(w: int, h: int) -> bytes:
    pil_img = Image.new(mode='RGB', size=(w, h))
    with tempfile.NamedTemporaryFile('wb') as wh:
        pil_img.save(wh.name, 'BMP')
        with open(wh.name, 'rb') as rh:
            return rh.read()


@functools.cache
def make_zip(filename: str, data: str, n: int) -> bytes:
    with tempfile.TemporaryDirectory() as tmp_dir:
        # create json
        json_path = os.path.join(tmp_dir, 'game.json')
        with open(json_path, 'w') as jh:
            jh.write(data)
        # create image
        for i in range(n):
            img_path = os.path.join(tmp_dir, '{0}.bmp'.format(i))
            img_file = Image.new(mode='RGB', size=(1024, 1024))
            img_file.save(img_path)
        # pack zip
        zip_path = os.path.join(tmp_dir, '{0}.zip'.format(filename))
        with zipfile.ZipFile(zip_path, "w") as zh:
            zh.write(json_path, 'game.json')
            for i in range(n):
                zh.write(img_path, '{0}.bmp'.format(i))
        with open(zip_path, 'rb') as rh:
            return rh.read()


# ----------------------------------------------------------------------------------------------------------------------

class EngineBaseTest(unittest.TestCase):

    @staticmethod
    def defaultEnviron():
        os.environ['VTT_TITLE'] = 'unittest'
        os.environ['VTT_LIMIT_TOKEN'] =' 2'
        os.environ['VTT_LIMIT_BG'] = '10'
        os.environ['VTT_LIMIT_GAME'] = '5'
        os.environ['VTT_LIMIT_MUSIC'] = '10'
        os.environ['VTT_NUM_MUSIC'] = '5'
        os.environ['VTT_CLEANUP_EXPIRE'] = '3600'
        os.environ['VTT_CLEANUP_TIME'] = '03:00'
        os.environ['VTT_DOMAIN'] = 'vtt.example.com'
        os.environ['VTT_PORT'] = '8080'
        os.environ.pop('VTT_SSL', None)
        os.environ.pop('VTT_REVERSE_PROXY', None)

    def setUp(self) -> None:
        # create temporary directory
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmpdir.name)
        
        # pre-generate paths api for dummy files
        paths = PathApi(appname='unittest', pref_root=self.root)
        for w in ['verbs', 'adjectives', 'nouns']:
            with open(paths.get_fancy_url_path() / '{0}.txt'.format(w), 'w') as h:
                h.write('demo')
        
        # load engine app into webtest
        self.engine = Engine(argv=['--quiet', '--localhost'], pref_dir=self.root)
        self.engine.app.catchall = False
        self.app = webtest.TestApp(self.engine.app)
        
        self.monkeyPatch()
        EngineBaseTest.defaultEnviron()
                
    def monkeyPatch(self) -> None:
        # save methods for later
        self.prev_getPublicIp = self.engine.get_public_ip
        self.prev_getCountryFromIp = self.engine.get_country_from_ip
        # monkey-patch methods with stubs
        self.engine.get_public_ip = lambda: '?.?.?.?'
        self.engine.get_country_from_ip = lambda ip: 'unknown'
        
    def tearDown(self) -> None:
        # unload engine
        del self.app
        del self.engine
        del self.tmpdir

    def join_player(self, gm_url: str, game_url: str, player_name: str, player_color: str) -> tuple[any, PlayerCache]:
        # post login
        ret = self.app.post('/game/{0}/{1}/login'.format(gm_url, game_url),
                            {'playername': player_name, 'playercolor': player_color})
        self.assertEqual(ret.status_int, 200)
        # open fake socket
        s = SocketDummy()
        s.block = True
        s.push_receive({'name': player_name, 'gm_url': gm_url, 'game_url': game_url})
        # listen to the faked websocket
        return ret, self.engine.cache.listen(s)


# ---------------------------------------------------------------------

class SocketDummy:
    """Dummy class for working with a socket."""

    read_buffer: list[str]
    write_buffer: list[str]
    closed: False
    block: False
    
    def __init__(self) -> None:
        self.clear_all()
        
    def clear_all(self) -> None:
        self.read_buffer = list()
        self.write_buffer = list()
        
        self.closed = False
        self.block = True
        
    def receive(self) -> str | None:
        if self.closed:
            raise WebSocketError('SocketDummy is closed')
        # block if buffer empty
        while self.block and len(self.read_buffer) == 0:
            time.sleep(0.01)
        # yield buffer element
        if len(self.read_buffer) > 0:
            return self.read_buffer.pop(0)
        return None
        
    def push_receive(self, data: dict) -> None:
        self.read_buffer.append(json.dumps(data))
        
    def send(self, s: str) -> None:
        if self.closed:
            raise WebSocketError('SocketDummy is closed')
        self.write_buffer.append(s)
        
    def pop_send(self) -> dict | None:
        if len(self.write_buffer) > 0:
            return json.loads(self.write_buffer.pop(0))
        return None
        
    def close(self) -> None:
        if self.closed:
            raise WebSocketError('SocketDummy is closed')
        self.closed = True


# ---------------------------------------------------------------------

def pre_setup_unittest(argv: list[str]) -> list[str]:
    argv.append('--quiet')
    argv.append('--debug')
    argv.append('--localhost')
    return argv


def setup_unittest_routes(engine):
    @bottle.get('/vtt/unittest/game')
    @bottle.view('unittest_game')
    def unittest_demo_game():
        gm = engine.main_db.GM.select(lambda _gm: _gm.url == 'arthur').first()
        gm_cache = engine.cache.get_from_url('arthur')
        game = gm_cache.db.Game.select(lambda g: g.url == 'test-game-1').first()
            
        websocket_url = engine.get_websocket_url()
            
        return dict(engine=engine, user_agent='UNITTEST', websocket_url=websocket_url, game=game, playername='arthur',
                    playercolor='#FF0000', gm=gm, is_gm=True)

    # setup demo game
    # @TODO register GM arthur
    # @TODO create game test-game-1 with background "/static/background.jpg"
    
    server_uri = engine.get_url()
    print('=' * 80)
    print('URLs for Unittest scenarios:')
    for route in ['/vtt/unittest/game']:
        print('\t{0}{1}'.format(server_uri, route))
    print('=' * 80)
