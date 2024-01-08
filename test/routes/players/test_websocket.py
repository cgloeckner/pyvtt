"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

from test.common import EngineBaseTest, make_image
from vtt import routes


class WebsocketRoutesTest(EngineBaseTest):

    def setUp(self):
        super().setUp()
        routes.register_gm(self.engine)
        routes.register_player(self.engine)
        routes.register_resources(self.engine)
        routes.register_api(self.engine)
        # @NOTE: custom error pages are not routed here

        # @NOTE establishing a websocket is not tested atm
        # instead the method dispatching is tested

        # register arthur
        ret = self.app.post('/vtt/join', {'gmname': 'arthur'}, xhr=True)
        self.assertEqual(ret.status_int, 200)

        # create a game
        img_small = make_image(512, 512)
        ret = self.app.post('/vtt/import-game/test-game-1', upload_files=[('file', 'test.png', img_small)], xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.app.reset()

        # First, the handles are monkey patched to add to a list instead
        self.log = list()
        gm_cache = self.engine.cache.get_from_url('arthur')
        self.game_cache = gm_cache.get_from_url('test-game-1')
        self.game_cache.on_ping = lambda p, d: self.log.append(('onPing', p, d))
        self.game_cache.on_roll = lambda p, d: self.log.append(('onRoll', p, d))
        self.game_cache.on_select = lambda p, d: self.log.append(('onSelect', p, d))
        self.game_cache.on_range = lambda p, d: self.log.append(('onRange', p, d))
        self.game_cache.on_order = lambda p, d: self.log.append(('onOrder', p, d))
        self.game_cache.on_update_token = lambda p, d: self.log.append(('onUpdateToken', p, d))
        self.game_cache.on_create_token = lambda p, d: self.log.append(('onCreateToken', p, d))
        self.game_cache.on_clone_token = lambda p, d: self.log.append(('onCloneToken', p, d))
        self.game_cache.on_delete_token = lambda p, d: self.log.append(('onDeleteToken', p, d))
        self.game_cache.on_beacon = lambda p, d: self.log.append(('onBeacon', p, d))
        self.game_cache.on_music = lambda p, d: self.log.append(('onMusic', p, d))
        self.game_cache.on_create_scene = lambda p, d: self.log.append(('onCreateScene', p, d))
        self.game_cache.on_activate_scene = lambda p, d: self.log.append(('onActivateScene', p, d))
        self.game_cache.on_clone_scene = lambda p, d: self.log.append(('onCloneScene', p, d))
        self.game_cache.on_delete_scene = lambda p, d: self.log.append(('onDeleteScene', p, d))

    def test_supported_player_actions(self):
        ret, player_cache = self.join_player('arthur', 'test-game-1', 'merlin', '#FF00FF')
        s = player_cache.socket
        s.block = False
        opids = ['PING', 'ROLL', 'SELECT', 'RANGE', 'ORDER', 'UPDATE', 'CREATE', 'CLONE', 'DELETE', 'BEACON', 'MUSIC',
                 'GM-CREATE', 'GM-ACTIVATE', 'GM-CLONE', 'GM-DELETE']
        for opid in opids:
            s.push_receive({'OPID': opid, 'data': opid.lower()})
        player_cache.greenlet.join()

        # expect actions
        self.assertEqual(len(self.log), 15)
        self.assertEqual(self.log[0][0], 'onPing')
        self.assertEqual(self.log[1][0], 'onRoll')
        self.assertEqual(self.log[2][0], 'onSelect')
        self.assertEqual(self.log[3][0], 'onRange')
        self.assertEqual(self.log[4][0], 'onOrder')
        self.assertEqual(self.log[5][0], 'onUpdateToken')
        self.assertEqual(self.log[6][0], 'onCreateToken')
        self.assertEqual(self.log[7][0], 'onCloneToken')
        self.assertEqual(self.log[8][0], 'onDeleteToken')
        self.assertEqual(self.log[9][0], 'onBeacon')
        self.assertEqual(self.log[10][0], 'onMusic')
        self.assertEqual(self.log[11][0], 'onCreateScene')
        self.assertEqual(self.log[12][0], 'onActivateScene')
        self.assertEqual(self.log[13][0], 'onCloneScene')
        self.assertEqual(self.log[14][0], 'onDeleteScene')
        for i, opid in enumerate(opids):
            self.assertEqual(self.log[i][1], player_cache)
            self.assertEqual(self.log[i][2], {'OPID': opid, 'data': opid.lower()})

    def test_cannot_trigger_unknown_operation(self):
        ret, player_cache = self.join_player('arthur', 'test-game-1', 'merlin', '#FF00FF')
        s = player_cache.socket
        s.block = False
        s.push_receive({'OPID': 'fantasy', 'data': None})
        # expect exception is NOT killing the greenlet (= closing player session)
        self.assertEqual(len(self.log), 0)
    
    def test_cannot_trigger_operation_with_too_few_arguments(self):
        self.game_cache.on_roll = lambda p, d: self.log.append(('onRoll', p, d['sides']))
        ret, player_cache = self.join_player('arthur', 'test-game-1', 'merlin', '#FF00FF')
        s = player_cache.socket
        s.block = False
        s.push_receive({'OPID': 'ROLL'})  # not providing number of sides etc.
        # expect exception is NOT killing the greenlet (= closing player session)
        self.assertEqual(len(self.log), 0)
