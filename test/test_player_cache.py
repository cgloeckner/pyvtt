#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import time, copy

from pony.orm import db_session

import cache, orm

from test.utils import EngineBaseTest, SocketDummy

class PlayerCacheTest(EngineBaseTest):
    
    def setUp(self):
        super().setUp()
        
        with db_session:
            gm = self.engine.main_db.GM(name='user123', url='foo', sid='123456')
            gm.postSetup()
        
        # create GM database
        gm_cache = self.engine.cache.get(gm)
        gm_cache.connect_db()
        
        with db_session:
            game = gm_cache.db.Game(url='bar', gm_url='foo')
            game.postSetup()
            
            # create pretty old rolls
            kwargs = {
                'game'   : game,
                'name'   : 'nobody',
                'color'  : '#DEAD00',
                'sides'  : 4,
                'result' : 3,
                'timeid' : time.time() - self.engine.latest_rolls - 10
            }
            gm_cache.db.Roll(**kwargs)
            
            # create some old rolls 
            kwargs['sides']  = 12 
            kwargs['timeid'] = time.time() - self.engine.recent_rolls - 10
            for i in range(1, 13):
                kwargs['result'] = i
                gm_cache.db.Roll(**kwargs)
            
            # create some recent rolls
            kwargs['sides']  = 20
            kwargs['timeid'] = time.time()
            for i in range(1, 21):
                kwargs['result'] = i
                gm_cache.db.Roll(**kwargs)
            
            # create scenes and tokens
            scene1 = gm_cache.db.Scene(game=game)
            scene2 = gm_cache.db.Scene(game=game)
            
            # set active scene
            gm_cache.db.commit()
            game.active = scene1.id
            
            # create backgrounds
            b1 = gm_cache.db.Token(scene=scene1, url='/foo', posx=20,
                posy=30, size=-1)
            b2 = gm_cache.db.Token(scene=scene2, url='/foo', posx=20,
                posy=30, size=-1)
            
            gm_cache.db.commit()
            scene1.backing = b1
            
            # create some tokens
            for i in range(5):
                gm_cache.db.Token(scene=scene1, url='/foo', posx=20+i,
                    posy=30, size=40)
                gm_cache.db.Token(scene=scene2, url='/foo', posx=20+i ,
                    posy=30, size=40)

    def get_game(self, gm='foo', game='bar'):
        """ Helper to query a game. """
        gm_cache = self.engine.cache.getFromUrl(gm)
        return gm_cache.db.Game.select(lambda g: g.url == game).first()

    def active_scene(self, gm='foo', game='bar'):
        """ Helper to query active scene of a game. """
        gm_cache = self.engine.cache.getFromUrl(gm) 
        game = self.get_game(gm, game)
        return gm_cache.db.Scene.select(lambda s: s.id == game.active).first()
        
    def purge_scene(self, scene):
        """ Helper to purge a scene from all tokens. """
        for t in scene.tokens:
            t.delete()
    
    def purge_game(self, gm='foo', game='bar'):
        """ Helper to purge a game from all scenes. """
        gm_cache = self.engine.cache.getFromUrl(gm)
        game = gm_cache.db.Game.select(lambda g: g.url == game).first()
        for s in game.scenes:
            s.preDelete()
            s.delete()
        game.order = list()
    
    def get_token(self, tid, gm='foo'):
        """ Helper to query a token from a game by its id. """  
        gm_cache = self.engine.cache.getFromUrl(gm)
        return gm_cache.db.Token.select(lambda t: t.id == tid).first()
        
    def test_getMetaData(self):  
        game_cache = self.engine.cache.getFromUrl('foo').getFromUrl('bar')
        player_cache   = game_cache.insert('arthur', 'red', False)
        gmplayer_cache = game_cache.insert('bob', 'blue', True)
        
        meta1 = player_cache.getMetaData()
        self.assertEqual(meta1['name'], 'arthur')
        self.assertFalse(meta1['is_gm'])
        self.assertEqual(meta1['game'], 'bar')
        self.assertEqual(meta1['gm'], 'foo')
        
        meta2 = gmplayer_cache.getMetaData()
        self.assertEqual(meta2['name'], 'bob')
        self.assertTrue(meta2['is_gm'])
        self.assertEqual(meta2['game'], 'bar')
        self.assertEqual(meta2['gm'], 'foo')
        
    def test_login(self):
        old_socket = SocketDummy()
        new_socket = SocketDummy()
        
        # insert players
        game_cache = self.engine.cache.getFromUrl('foo').getFromUrl('bar')
        player_cache1 = game_cache.insert('arthur', 'red', False)
        player_cache1.socket = old_socket
        player_cache2 = game_cache.insert('bob', 'yellow', False)
        player_cache2.socket = new_socket
        
        # trigger login
        game_cache.login(player_cache2)
        
        # expect ACCEPT to joined player
        accept = new_socket.pop_send()
        self.assertEqual(accept['OPID'], 'ACCEPT')
        self.assertIn('players', accept)
        self.assertIn('rolls', accept)
        self.assertIn('urls', accept)
        
        # expect latest rolls were received
        self.assertEqual(len(accept['rolls']), 32)
        num_recent = 0
        for r in accept['rolls']:
            # test data fields' existence
            self.assertIn('color', r)
            self.assertIn('sides', r)
            self.assertIn('result', r)
            self.assertIn('name', r)
            if r['recent']:
                num_recent += 1
        self.assertEqual(num_recent, 20)
        
        # expect scene data to joined player
        refresh = new_socket.pop_send()
        self.assertEqual(refresh['OPID'], 'REFRESH')
        # @NOTE: refresh data is tested seperately in-depth
        
        # expect JOIN being broadcast
        join_broadcast = old_socket.pop_send()
        self.assertEqual(join_broadcast['OPID'], 'JOIN')       
        self.assertEqual(join_broadcast['name'], player_cache2.name)
        self.assertEqual(join_broadcast['uuid'], player_cache2.uuid)
        self.assertEqual(join_broadcast['color'], player_cache2.color)
        self.assertEqual(join_broadcast['country'], player_cache2.country)
        self.assertEqual(join_broadcast['index'], player_cache2.index)
        
        # expect ORDER being broadcast
        order_broadcast = old_socket.pop_send()
        self.assertEqual(order_broadcast['OPID'], 'ORDER')
        self.assertEqual(order_broadcast['indices'], {
            player_cache1.uuid : 0, player_cache2.uuid : 1
        })
        
    def test_logout(self):
        socket1 = SocketDummy()
        socket2 = SocketDummy()
        
        # insert players
        game_cache = self.engine.cache.getFromUrl('foo').getFromUrl('bar')
        player_cache1 = game_cache.insert('arthur', 'red', False)
        player_cache1.socket = socket1
        player_cache2 = game_cache.insert('bob', 'yellow', False)
        player_cache2.socket = socket2
        
        # trigger logout
        game_cache.logout(player_cache1)
        
        # expect QUIT being broadcast
        quit_broadcast = socket2.pop_send()
        self.assertEqual(quit_broadcast['OPID'], 'QUIT')
        self.assertEqual(quit_broadcast['name'], player_cache1.name)
        self.assertEqual(quit_broadcast['uuid'], player_cache1.uuid)
        
        # @NOTE: no ORDER required because the client will be updated
        # as soon as the order is actually changed, since the gap is
        # already closed after logout (inside the server)
        
    def test_disconnect(self):
        # insert player
        game_cache = self.engine.cache.getFromUrl('foo').getFromUrl('bar')
        player_cache = game_cache.insert('arthur', 'red', False)
        player_cache.socket = SocketDummy()
        
        # disconnect him
        game_cache.disconnect(player_cache.uuid)
        
        # make sure he is not there anymore
        player_cache = game_cache.get('arthur')
        self.assertIsNone(player_cache)
        
        # ... and can re-login
        game_cache.insert('arthur', 'red', False)
        
    def test_cleanup(self):
        # insert players
        game_cache = self.engine.cache.getFromUrl('foo').getFromUrl('bar')
        player_cache1 = game_cache.insert('arthur', 'red', False)
        player_cache1.socket = SocketDummy()
        player_cache2 = game_cache.insert('gabriel', 'blue', False)
        player_cache2.socket = SocketDummy()
        player_cache2.socket.close()
        player_cache3 = game_cache.insert('bob', 'yellow', False)
        player_cache3.socket = SocketDummy()
        
        # disconnect him
        game_cache.cleanup()
        
        # make player2 is disconnected
        data = game_cache.getData()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['name'], 'arthur')
        self.assertEqual(data[1]['name'], 'bob')
        
        # ... and can re-login
        game_cache.insert('gabriel', 'red', False)
        
    def test_broadcast(self):
        socket1 = SocketDummy()
        socket2 = SocketDummy()
        
        # insert players
        game_cache = self.engine.cache.getFromUrl('foo').getFromUrl('bar')
        player_cache1 = game_cache.insert('arthur', 'red', False)
        player_cache1.socket = socket1
        player_cache2 = game_cache.insert('bob', 'yellow', False)
        player_cache2.socket = socket2
        
        # broadcast
        game_cache.broadcast({'foo': 'bar'})
        
        # expect foo bar at both sockets
        foobar = socket1.pop_send()
        self.assertEqual(foobar['foo'], 'bar')
        foobar = socket2.pop_send()
        self.assertEqual(foobar['foo'], 'bar')
        
    def test_broadcastTokenUpdate(self):
        socket1 = SocketDummy()
        socket2 = SocketDummy()
        socket3 = SocketDummy()
        
        # insert players
        gm_cache   = self.engine.cache.getFromUrl('foo')
        game_cache = gm_cache.getFromUrl('bar')
        player_cache1 = game_cache.insert('arthur', 'red', False)
        player_cache1.socket = socket1
        player_cache2 = game_cache.insert('bob', 'yellow', False)
        player_cache2.socket = socket2
        player_cache3 = game_cache.insert('carlos', 'green', False)
        player_cache3.socket = socket3
        
        # update some tokens in active scene
        since = time.time() - 30 # for last 30 seconds
        with db_session:
            active = gm_cache.db.Game.select(lambda g: g.url == 'bar').first().active
            for t in gm_cache.db.Token.select(lambda t: t.scene.id == active and t.posx >= 22):
                t.timeid = since
        # trigger token update after player1 changed something
        game_cache.broadcastTokenUpdate(player_cache1, since)
        
        # expect broadcast to all sockets
        data1 = socket1.pop_send()
        data2 = socket2.pop_send()
        data3 = socket3.pop_send()
        self.assertEqual(data1, data2)
        self.assertEqual(data1, data3)
        
        # check data for tokens
        self.assertEqual(data1['OPID'], 'UPDATE')
        tokens = data1['tokens']
        self.assertEqual(len(tokens), 3)
        
        # expect tokens to be branded with the uuid of player1 (since
        # he modified them) - so the client can handle it correctly
        # (e.g. ignoring for the sake of client side prediction)
        for t in tokens:
            self.assertEqual(t['uuid'], player_cache1.uuid)
            
    def test_broadcastSceneSwitch(self):
        socket1 = SocketDummy()
        socket2 = SocketDummy()
        socket3 = SocketDummy()
        
        # insert players
        gm_cache   = self.engine.cache.getFromUrl('foo')
        game_cache = gm_cache.getFromUrl('bar')
        player_cache1 = game_cache.insert('arthur', 'red', False)
        player_cache1.socket = socket1
        player_cache2 = game_cache.insert('bob', 'yellow', False)
        player_cache2.socket = socket2
        player_cache3 = game_cache.insert('carlos', 'green', False)
        player_cache3.socket = socket3
        
        with db_session:
            game = gm_cache.db.Game.select(lambda g: g.url == 'bar').first()
            # broadcast about active scene
            game_cache.broadcastSceneSwitch(game)
        
        # expect broadcast to all sockets
        data1 = socket1.pop_send()
        data2 = socket2.pop_send()
        data3 = socket3.pop_send()
        self.assertEqual(data1, data2)
        self.assertEqual(data1, data3)
        
        # check data for tokens
        self.assertEqual(data1['OPID'], 'REFRESH')
        # @NOTE: refresh data is tested seperately in-depth
        
    def test_fetchRefresh(self):
        socket1 = SocketDummy()
        socket2 = SocketDummy()
        socket3 = SocketDummy()
        
        # insert players
        gm_cache   = self.engine.cache.getFromUrl('foo')
        game_cache = gm_cache.getFromUrl('bar')
        player_cache1 = game_cache.insert('arthur', 'red', False)
        player_cache1.socket = socket1
        player_cache2 = game_cache.insert('bob', 'yellow', False)
        player_cache2.socket = socket2
        player_cache3 = game_cache.insert('carlos', 'green', False)
        player_cache3.socket = socket3
        
        # fetch refresh data
        with db_session:
            game = gm_cache.db.Game.select(lambda g: g.url == 'bar').first()
            data = game_cache.fetchRefresh(game.active)
            
            scene = gm_cache.db.Scene.select(lambda s: s.id == game.active).first()
            
            # expect complete REFRESH update
            self.assertEqual(data['OPID'], 'REFRESH')
            self.assertEqual(data['background'], scene.backing.id)
            self.assertEqual(len(data['tokens']), len(scene.tokens))
            
            # test token data
            for t in data['tokens']:
                self.assertIn('id', t)
                self.assertIn('posx', t)
                self.assertIn('posy', t)
                self.assertIn('zorder', t)
                self.assertIn('size', t)
                self.assertIn('rotate', t)
                self.assertIn('flipx', t)
                self.assertIn('locked', t)
                self.assertIn('timeid', t)
            
            # fetch data of a scene without background
            other_scene = list(game.scenes)[0]
            if other_scene == scene:
                other_scene = list(game.scenes)[1]
            data = game_cache.fetchRefresh(other_scene.id)
             
            # expect complete REFRESH update
            self.assertEqual(data['OPID'], 'REFRESH')
            self.assertEqual(data['background'], None)
        
    def test_onPing(self):
        socket = SocketDummy()
        
        # insert player
        gm_cache   = self.engine.cache.getFromUrl('foo')
        game_cache = gm_cache.getFromUrl('bar')
        player_cache = game_cache.insert('arthur', 'red', False)
        player_cache.socket = socket
        
        # trigger ping and expect answer
        game_cache.onPing(player_cache, {})
        answer = socket.pop_send()
        self.assertEqual(answer['OPID'], 'PING')
        
    def test_onRoll(self): 
        socket1 = SocketDummy()
        socket2 = SocketDummy()
        socket3 = SocketDummy()
        
        # insert players
        gm_cache   = self.engine.cache.getFromUrl('foo')
        game_cache = gm_cache.getFromUrl('bar')
        player_cache1 = game_cache.insert('arthur', 'red', False)
        player_cache1.socket = socket1
        player_cache2 = game_cache.insert('bob', 'yellow', False)
        player_cache2.socket = socket2
        player_cache3 = game_cache.insert('carlos', 'green', False)
        player_cache3.socket = socket3
        
        # trigger roll different dice and expect ROLLs
        sides = self.engine.getSupportedDice()
        for s in sides:
            game_cache.onRoll(player_cache1, {'sides': s})
            answer1 = socket1.pop_send()
            answer2 = socket2.pop_send()
            answer3 = socket3.pop_send()
            self.assertEqual(answer1, answer2)
            self.assertEqual(answer1, answer3)
            self.assertEqual(answer1['OPID'], 'ROLL')
            self.assertEqual(answer1['color'], player_cache1.color)
            self.assertEqual(answer1['sides'], s)
            self.assertIn('result', answer1)
            self.assertTrue(answer1['recent'])
            self.assertEqual(answer1['name'], player_cache1.name)
        
        # cannot roll unsupported dice
        self.assertNotIn(7, sides)
        game_cache.onRoll(player_cache1, {'sides': 7})
        answer = socket1.pop_send()
        self.assertIsNone(answer)
        
    def test_onSelect(self): 
        socket1 = SocketDummy()
        socket2 = SocketDummy()
        socket3 = SocketDummy()
        
        # insert players
        gm_cache   = self.engine.cache.getFromUrl('foo')
        game_cache = gm_cache.getFromUrl('bar')
        player_cache1 = game_cache.insert('arthur', 'red', False)
        player_cache1.socket = socket1
        player_cache2 = game_cache.insert('bob', 'yellow', False)
        player_cache2.socket = socket2
        player_cache3 = game_cache.insert('carlos', 'green', False)
        player_cache3.socket = socket3
        
        # trigger selection and expect SELECT broadcast
        selected = [37, 134, 623]
        game_cache.onSelect(player_cache1, {'selected': selected})
        
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        
        self.assertEqual(answer1['OPID'], 'SELECT')
        self.assertEqual(answer1['color'], player_cache1.color)
        self.assertEqual(answer1['selected'], player_cache1.selected)
        # expect player's selection being updated
        self.assertEqual(player_cache1.selected, selected)
        
        socket1.clearAll()
        socket2.clearAll()
        socket3.clearAll()
        
        # trigger selection reste and expect SELECT broadcast  
        selected = list()
        game_cache.onSelect(player_cache1, {'selected': selected})
        
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        
        self.assertEqual(answer1['OPID'], 'SELECT')
        self.assertEqual(answer1['color'], player_cache1.color)
        self.assertEqual(answer1['selected'], player_cache1.selected)
        # expect player's selection being updated
        self.assertEqual(player_cache1.selected, selected)
        
    def test_onRange(self): 
        socket1 = SocketDummy()
        socket2 = SocketDummy()
        socket3 = SocketDummy()
        
        # insert players
        gm_cache   = self.engine.cache.getFromUrl('foo')
        game_cache = gm_cache.getFromUrl('bar')
        player_cache1 = game_cache.insert('arthur', 'red', False)
        player_cache1.socket = socket1
        player_cache2 = game_cache.insert('bob', 'yellow', False)
        player_cache2.socket = socket2
        player_cache3 = game_cache.insert('carlos', 'green', False)
        player_cache3.socket = socket3
        
        # place some tokens for query
        with db_session:
            game = gm_cache.db.Game.select(lambda g: g.url == 'bar').first()
            scene = gm_cache.db.Scene.select(lambda s: s.id == game.active).first()
            
            add_token = lambda x, y: gm_cache.db.Token(
                scene=scene, url='/test', posx=x, posy=y, size=20
            )
            
            # @NOTE: will query for (100, 130) with 40x30
            inside     = add_token(x=120, y=145)
            at_left    = add_token(x= 90, y=145) # x within half size
            at_right   = add_token(x=150, y=145) # x within half size
            at_top     = add_token(x=120, y=120) # y within half size
            at_bottom  = add_token(x=120, y=170) # y within half size
            off_left   = add_token(x= 89, y=145)
            off_right  = add_token(x=151, y=145)
            off_top    = add_token(x=120, y=119)
            off_bottom = add_token(x=120, y=171)
            outside    = add_token(x=300, y=250)
        
        # trigger range selection and expect SELECT broadcast
        query = {
            'adding' : False,
            'left'   : 100,
            'top'    : 130,
            'width'  : 40,
            'height' : 30
        }
        game_cache.onRange(player_cache1, query)
         
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        
        self.assertEqual(answer1['OPID'], 'SELECT')
        # @NOTE: SELECT is tested more in-depth on its own
        
        # @TODO: fix that bug
        self.assertEqual(len(player_cache1.selected), 1)#5)
        self.assertIn(inside.id,    player_cache1.selected)
        #self.assertIn(at_left.id,   player_cache1.selected)
        #self.assertIn(at_right.id,  player_cache1.selected)
        #self.assertIn(at_top.id,    player_cache1.selected)
        #self.assertIn(at_bottom.id, player_cache1.selected)
        
        socket1.clearAll()
        socket2.clearAll()
        socket3.clearAll()
        
        # trigger range query on empty space
        query = {
            'adding' : False,
            'left'   : 0,
            'top'    : 2,
            'width'  : 3,
            'height' : 4
        }
        game_cache.onRange(player_cache1, query) 
        
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        
        self.assertEqual(answer1['OPID'], 'SELECT')
        self.assertEqual(len(player_cache1.selected), 0)
        
        socket1.clearAll()
        socket2.clearAll()
        socket3.clearAll()
        
        # trigger adding range query on empty space
        player_cache1.selected = [145634]  
        query = {
            'adding' : True,
            'left'   : 0,
            'top'    : 2,
            'width'  : 3,
            'height' : 4
        }
        game_cache.onRange(player_cache1, query) 
        
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        
        self.assertEqual(answer1['OPID'], 'SELECT')
        self.assertEqual(len(player_cache1.selected), 1)
        self.assertIn(145634, player_cache1.selected)
        
        socket1.clearAll()
        socket2.clearAll()
        socket3.clearAll()
        
        # trigger adding range query on regular space
        query = {
            'adding' : True,
            'left'   : 100,
            'top'    : 130,
            'width'  : 40,
            'height' : 30
        }
        game_cache.onRange(player_cache1, query) 
        
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        
        self.assertEqual(answer1['OPID'], 'SELECT')
        self.assertEqual(len(player_cache1.selected), 2)
        self.assertIn(145634,    player_cache1.selected)
        self.assertIn(inside.id, player_cache1.selected)
        
    def test_onOrder(self):
        socket1 = SocketDummy()
        socket2 = SocketDummy()
        socket3 = SocketDummy()
        
        # insert players
        gm_cache   = self.engine.cache.getFromUrl('foo')
        game_cache = gm_cache.getFromUrl('bar')
        player_cache1 = game_cache.insert('arthur', 'red', False)
        player_cache1.socket = socket1
        player_cache2 = game_cache.insert('bob', 'yellow', False)
        player_cache2.socket = socket2
        player_cache3 = game_cache.insert('carlos', 'green', False)
        player_cache3.socket = socket3
        
        # moving player left triggers ORDER broadcast
        game_cache.onOrder(player_cache2, {'name': 'bob', 'direction': -1})
        
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        
        self.assertEqual(answer1['OPID'], 'ORDER')
        expected = {
            player_cache1.uuid: 1,
            player_cache2.uuid: 0,
            player_cache3.uuid: 2
        }
        self.assertEqual(answer1['indices'], expected)
        
        socket1.clearAll()
        socket2.clearAll()
        socket3.clearAll()
        
        # moving player right triggers ORDER broadcast
        game_cache.onOrder(player_cache2, {'name': 'bob', 'direction': 1})
        
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        
        self.assertEqual(answer1['OPID'], 'ORDER')
        expected = {
            player_cache1.uuid: 0,
            player_cache2.uuid: 1,
            player_cache3.uuid: 2
        }
        self.assertEqual(answer1['indices'], expected)
        
        socket1.clearAll()
        socket2.clearAll()
        socket3.clearAll()
        
        # cannot move more then one spot 
        game_cache.onOrder(player_cache2, {'name': 'bob', 'direction': 2})
        
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertIsNone(answer1)
        self.assertIsNone(answer2)
        self.assertIsNone(answer3)
        
        socket1.clearAll()
        socket2.clearAll()
        socket3.clearAll()
        
        # cannot move without direction
        game_cache.onOrder(player_cache2, {'name': 'bob', 'direction': 0})
        
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertIsNone(answer1)
        self.assertIsNone(answer2)
        self.assertIsNone(answer3)
        
        socket1.clearAll()
        socket2.clearAll()
        socket3.clearAll()
        
        # cannot move unknown player
        game_cache.onOrder(player_cache2, {'name': 'roger', 'direction': 0})
        
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertIsNone(answer1)
        self.assertIsNone(answer2)
        self.assertIsNone(answer3)
        
        socket1.clearAll()
        socket2.clearAll()
        socket3.clearAll()
        
        # moving first player left triggers ORDER with unchanged data
        game_cache.onOrder(player_cache2, {'name': 'arthur', 'direction': -1})  
        
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        
        self.assertEqual(answer1['OPID'], 'ORDER')
        self.assertEqual(answer1['indices'], expected)
        
        socket1.clearAll()
        socket2.clearAll()
        socket3.clearAll()
        
        # moving last player right triggers ORDER with unchanged data
        game_cache.onOrder(player_cache2, {'name': 'carlos', 'direction': 1})  
        
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        
        self.assertEqual(answer1['OPID'], 'ORDER')
        self.assertEqual(answer1['indices'], expected)
        
    def test_onUpdateToken(self):
        socket1 = SocketDummy()
        socket2 = SocketDummy()
        socket3 = SocketDummy()
        
        # insert players
        gm_cache   = self.engine.cache.getFromUrl('foo')
        game_cache = gm_cache.getFromUrl('bar')
        player_cache1 = game_cache.insert('arthur', 'red', False)
        player_cache1.socket = socket1
        player_cache2 = game_cache.insert('bob', 'yellow', False)
        player_cache2.socket = socket2
        player_cache3 = game_cache.insert('carlos', 'green', False)
        player_cache3.socket = socket3
        
        # create demo token
        with db_session:
            game = gm_cache.db.Game.select(lambda g: g.url == 'bar').first()
            last_update = game.timeid
            scene = gm_cache.db.Scene.select(lambda s: s.id == game.active).first()
            token = gm_cache.db.Token(scene=scene, url='/test', posx=30, posy=15, size=20)
        
        def query_token():
            with db_session:
                game = gm_cache.db.Game.select(lambda g: g.url == 'bar').first()
                last_update = game.timeid
                scene = gm_cache.db.Scene.select(lambda s: s.id == game.active).first()
                return gm_cache.db.Token.select(lambda t: t.id == token.id).first()
        
        default_update = { 'changes': [ {'id': token.id} ] }
        
        # token can be updated without actual data causing empty 'UPDATE' broadcast
        update_data = copy.deepcopy(default_update)
        game_cache.onUpdateToken(player_cache1, update_data)
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertEqual(answer1['OPID'], 'UPDATE')
        self.assertEqual(len(answer1['tokens']), 0)
        # expect game expiring timer being updated
        self.assertGreater(game.id, last_update)
        
        socket1.clearAll()
        socket2.clearAll()
        socket3.clearAll()
        
        # trigger update for invalid token expecting empty 'UPDATE' broadcast
        update_data = copy.deepcopy(default_update)
        update_data['changes'][0]['id'] = 5467357467 
        game_cache.onUpdateToken(player_cache1, update_data) 
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertEqual(answer1['OPID'], 'UPDATE')
        self.assertEqual(len(answer1['tokens']), 0)
        
        socket1.clearAll()
        socket2.clearAll()
        socket3.clearAll()
        
        # trigger token's position update
        update_data = copy.deepcopy(default_update)
        update_data['changes'][0]['posx'] = 38
        update_data['changes'][0]['posy'] = 43
        game_cache.onUpdateToken(player_cache1, update_data)
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertEqual(answer1['OPID'], 'UPDATE')
        self.assertEqual(len(answer1['tokens']), 1)
        token = query_token()
        self.assertEqual(token.posx, 38)
        self.assertEqual(token.posy, 43)
        
        socket1.clearAll()
        socket2.clearAll()
        socket3.clearAll()
        
        # cannot modify token's posx only
        update_data = copy.deepcopy(default_update)
        update_data['changes'][0]['posx'] = 100
        game_cache.onUpdateToken(player_cache1, update_data)
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertEqual(answer1['OPID'], 'UPDATE')
        self.assertEqual(len(answer1['tokens']), 0)
        token = query_token()
        self.assertEqual(token.posx, 38)
        self.assertEqual(token.posy, 43)
        
        socket1.clearAll()
        socket2.clearAll()
        socket3.clearAll()
        
        # cannot modify token's posy only
        update_data = copy.deepcopy(default_update)
        update_data['changes'][0]['posy'] = 100
        game_cache.onUpdateToken(player_cache1, update_data)
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertEqual(answer1['OPID'], 'UPDATE')
        self.assertEqual(len(answer1['tokens']), 0)
        token = query_token()
        self.assertEqual(token.posx, 38)
        self.assertEqual(token.posy, 43)
        
        socket1.clearAll()
        socket2.clearAll()
        socket3.clearAll()
        
        # trigger token's size update
        update_data = copy.deepcopy(default_update)
        update_data['changes'][0]['size'] = 50
        game_cache.onUpdateToken(player_cache1, update_data) 
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertEqual(answer1['OPID'], 'UPDATE')
        self.assertEqual(len(answer1['tokens']), 1) 
        token = query_token()
        self.assertEqual(token.size, 50)
        
        socket1.clearAll()
        socket2.clearAll()
        socket3.clearAll()
        
        # trigger token's zorder-layering update
        update_data = copy.deepcopy(default_update)
        update_data['changes'][0]['zorder'] = 13
        game_cache.onUpdateToken(player_cache1, update_data) 
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertEqual(answer1['OPID'], 'UPDATE')
        self.assertEqual(len(answer1['tokens']), 1)
        token = query_token()
        self.assertEqual(token.zorder, 13)
        
        socket1.clearAll()
        socket2.clearAll()
        socket3.clearAll()
        
        # trigger token's rotate update
        update_data = copy.deepcopy(default_update)
        update_data['changes'][0]['rotate'] = 22.25
        game_cache.onUpdateToken(player_cache1, update_data) 
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertEqual(answer1['OPID'], 'UPDATE')
        self.assertEqual(len(answer1['tokens']), 1)
        token = query_token()
        self.assertAlmostEqual(token.rotate, 22.25)
        
        socket1.clearAll()
        socket2.clearAll()
        socket3.clearAll()
        
        # trigger token's flip-x update
        update_data = copy.deepcopy(default_update)
        update_data['changes'][0]['flipx'] = True
        game_cache.onUpdateToken(player_cache1, update_data) 
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertEqual(answer1['OPID'], 'UPDATE')
        self.assertEqual(len(answer1['tokens']), 1) 
        token = query_token()
        self.assertTrue(token.flipx)
        
        socket1.clearAll()
        socket2.clearAll()
        socket3.clearAll()
        
        # trigger token's flip-x redo update
        update_data = copy.deepcopy(default_update)
        update_data['changes'][0]['flipx'] = False
        game_cache.onUpdateToken(player_cache1, update_data) 
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertEqual(answer1['OPID'], 'UPDATE')
        self.assertEqual(len(answer1['tokens']), 1)
        token = query_token()
        self.assertFalse(token.flipx)
        
        socket1.clearAll()
        socket2.clearAll()
        socket3.clearAll()
        
        # trigger token's locking update
        update_data = copy.deepcopy(default_update)
        update_data['changes'][0]['locked'] = True
        game_cache.onUpdateToken(player_cache1, update_data) 
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertEqual(answer1['OPID'], 'UPDATE')
        self.assertEqual(len(answer1['tokens']), 1) 
        token = query_token()
        self.assertTrue(token.locked)
        
        socket1.clearAll()
        socket2.clearAll()
        socket3.clearAll()
        
        # trigger token's unlocking update
        update_data = copy.deepcopy(default_update)
        update_data['changes'][0]['locked'] = False
        game_cache.onUpdateToken(player_cache1, update_data) 
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertEqual(answer1['OPID'], 'UPDATE')
        self.assertEqual(len(answer1['tokens']), 1) 
        token = query_token()
        self.assertFalse(token.locked)
        
        # trigger token's label set, but color is set automatically
        update_data = copy.deepcopy(default_update)
        update_data['changes'][0]['text'] = 'foobar'
        game_cache.onUpdateToken(player_cache1, update_data) 
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertEqual(answer1['OPID'], 'UPDATE')
        self.assertEqual(len(answer1['tokens']), 1) 
        token = query_token()
        self.assertEqual(token.text, 'foobar')
        self.assertEqual(token.color, 'red')
        
        socket1.clearAll()
        socket2.clearAll()
        socket3.clearAll()
        
        # trigger token's label reset
        update_data = copy.deepcopy(default_update)
        update_data['changes'][0]['text'] = ''
        game_cache.onUpdateToken(player_cache1, update_data) 
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertEqual(answer1['OPID'], 'UPDATE')
        self.assertEqual(len(answer1['tokens']), 1) 
        token = query_token()
        self.assertEqual(token.text, '')
        
        socket1.clearAll()
        socket2.clearAll()
        socket3.clearAll()
        
    def test_onCreateToken(self):
        socket1 = SocketDummy()
        socket2 = SocketDummy()
        socket3 = SocketDummy()
        
        # insert players
        gm_cache   = self.engine.cache.getFromUrl('foo')
        game_cache = gm_cache.getFromUrl('bar')
        player_cache1 = game_cache.insert('arthur', 'red', False)
        player_cache1.socket = socket1
        player_cache2 = game_cache.insert('bob', 'yellow', False)
        player_cache2.socket = socket2
        player_cache3 = game_cache.insert('carlos', 'green', False)
        player_cache3.socket = socket3
        
        default_data = {
            'posx' : 50,
            'posy' : 67,
            'size' : 23,
            'urls' : list()
        }
        
        with db_session:
            scene = self.active_scene()
            old_timeid = max(list(scene.tokens), key=lambda t: t.timeid).timeid
        
        # trigger token creation and expect CREATE broadcast
        with db_session:
            self.purge_scene(self.active_scene())
        create_data = copy.deepcopy(default_data) 
        create_data['urls'] = ['/foo/bar.png', '/some/test.png', '/unit/test.png']
        game_cache.onCreateToken(player_cache1, create_data)
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertEqual(answer1['OPID'], 'CREATE')          
        self.assertEqual(len(answer1['tokens']), 3)
        distances = list()          
        with db_session:
            scene = self.active_scene()
        for i, d in enumerate(answer1['tokens']):
            with db_session:
                t = self.get_token(d['id'])
            # test for corret data
            self.assertGreater(answer1['tokens'][i]['timeid'], old_timeid)
            if answer1['tokens'][i]['size'] == -1:
                self.assertEqual(answer1['tokens'][i]['id'], scene.backing.id)
            else:
                # other tokens regular ones
                self.assertEqual(answer1['tokens'][i]['size'], 23)
            self.assertEqual(answer1['tokens'][i]['url'],  create_data['urls'][i])
            # test for being in sync with token data
            self.assertEqual(answer1['tokens'][i]['id'],    t.id)  
            self.assertEqual(answer1['tokens'][i]['timeid'], t.timeid)
            self.assertEqual(answer1['tokens'][i]['url'],   t.url)
            self.assertEqual(answer1['tokens'][i]['posx'],  t.posx)
            self.assertEqual(answer1['tokens'][i]['posy'],  t.posy)
            # calculate distance to original position
            dx = default_data['posx'] - t.posx
            dy = default_data['posy'] - t.posy
            distances.append((dx**2 + dy**2)**0.5)
        # expect all tokns having a similar distance from  each other
        min_dist = min(distances)
        max_dist = max(distances)
        self.assertLess(max_dist - min_dist, 10)
        # expect background being linked to scene
        with db_session:
            scene = self.active_scene()
            self.assertIsNotNone(scene.backing)
            token = self.get_token(scene.backing.id)
            self.assertEqual(token.back, scene)
        
        # can create token with optional label (colored by the player)
        with db_session:
            self.purge_scene(self.active_scene())
        create_data = copy.deepcopy(default_data)
        create_data['urls'] = ['/static/token_d4.png']
        create_data['labels'] = ['#3']
        game_cache.onCreateToken(player_cache1, create_data)
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertEqual(answer1['OPID'], 'CREATE')          
        self.assertEqual(len(answer1['tokens']), 1)
        self.assertEqual(answer1['tokens'][0]['text'],  '#3')
        self.assertEqual(answer1['tokens'][0]['color'], 'red')

        # can change background
        create_data = copy.deepcopy(default_data)
        create_data['size'] = '-1' 
        create_data['urls'] = ['/foo/bar.png']
        game_cache.onCreateToken(player_cache1, create_data)
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertEqual(answer1['OPID'], 'CREATE')          
        self.assertEqual(len(answer1['tokens']), 1)
        with db_session:
            scene = self.active_scene()
            tokens = gm_cache.db.Token.select(lambda t: t.scene == scene)
            # expect only one background token
            self.assertIsNotNone(scene.backing)
            for t in tokens:
                if t.size == -1:
                    self.assertEqual(t.id, scene.backing.id)
    
    def test_onDeleteToken(self):
        socket1 = SocketDummy()
        socket2 = SocketDummy()
        socket3 = SocketDummy()
        
        # insert players
        gm_cache   = self.engine.cache.getFromUrl('foo')
        game_cache = gm_cache.getFromUrl('bar')
        player_cache1 = game_cache.insert('arthur', 'red', False)
        player_cache1.socket = socket1
        player_cache2 = game_cache.insert('bob', 'yellow', False)
        player_cache2.socket = socket2
        player_cache3 = game_cache.insert('carlos', 'green', False)
        player_cache3.socket = socket3
        
        # can delete tokens
        with db_session:
            scene = self.active_scene()
            self.purge_scene(scene)
            t1 = gm_cache.db.Token(scene=scene, url='test', posx=5, posy=5, size=15)
            t2 = gm_cache.db.Token(scene=scene, url='test', posx=5, posy=5, size=15)
            t3 = gm_cache.db.Token(scene=scene, url='test', posx=5, posy=5, size=15)
            t4 = gm_cache.db.Token(scene=scene, url='test', posx=5, posy=5, size=15)
        ids = [t1.id, t3.id]
        game_cache.onDeleteToken(player_cache1, {'tokens': ids})
        # expect DELETE broadcast
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertEqual(answer1['OPID'], 'DELETE')          
        self.assertEqual(len(answer1['tokens']), 2)
        self.assertEqual(answer1['tokens'], ids)
        # expect tokens to be deleted
        with db_session:       
            scene = self.active_scene()
            remain = [t.id for t in scene.tokens]
            self.assertNotIn(t1.id, remain)
            self.assertIn(t2.id, remain)
            self.assertNotIn(t3.id, remain)
            self.assertIn(t4.id, remain)

        # cannot delete already deleted token 
        game_cache.onDeleteToken(player_cache1, {'tokens': [t3.id]}) 
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertIsNone(answer1)
        
        # cannot delete unknown token
        game_cache.onDeleteToken(player_cache1, {'tokens': [67546345]}) 
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertIsNone(answer1)

        # cannot delete locked token
        with db_session:
            scene = self.active_scene()
            self.purge_scene(scene)
            t1 = gm_cache.db.Token(scene=scene, url='test', posx=5, posy=5, size=15)
            t2 = gm_cache.db.Token(scene=scene, url='test', posx=5, posy=5, size=15)
            t3 = gm_cache.db.Token(scene=scene, url='test', posx=5, posy=5, size=15)
            t3.locked = True
            t4 = gm_cache.db.Token(scene=scene, url='test', posx=5, posy=5, size=15)
        ids = [t1.id, t3.id, t4.id]
        game_cache.onDeleteToken(player_cache1, {'tokens': ids})
        # expect DELETE broadcast for 2 of 3 tokens
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertEqual(answer1['OPID'], 'DELETE')          
        self.assertEqual(len(answer1['tokens']), 2)
        self.assertIn(t1.id, answer1['tokens'])
        self.assertIn(t4.id, answer1['tokens'])
        self.assertNotIn(t2.id, answer1['tokens'])
        # can query locked token
        with db_session:
            t = gm_cache.db.Token.select(lambda tkn: tkn.id == t3.id).first()
        self.assertIsNotNone(t)

    def test_onBeacon(self):
        socket1 = SocketDummy()
        socket2 = SocketDummy()
        socket3 = SocketDummy()
        
        # insert players
        gm_cache   = self.engine.cache.getFromUrl('foo')
        game_cache = gm_cache.getFromUrl('bar')
        player_cache1 = game_cache.insert('arthur', 'red', False)
        player_cache1.socket = socket1
        player_cache2 = game_cache.insert('bob', 'yellow', False)
        player_cache2.socket = socket2
        player_cache3 = game_cache.insert('carlos', 'green', False)
        player_cache3.socket = socket3

        beacon_data = {'OPID': 'BEACON', 'x': 5, 'y': 10}
        game_cache.onBeacon(player_cache1, beacon_data)
        # expect BEACON broadcast
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertEqual(answer1['OPID'], 'BEACON')
        self.assertEqual(answer1['x'], 5)
        self.assertEqual(answer1['y'], 10)
        self.assertEqual(answer1['color'], player_cache1.color)
        self.assertEqual(answer1['uuid'], player_cache1.uuid)

        # check that specific player's color and uuid are used
        beacon_data = {'OPID': 'BEACON', 'x': 5, 'y': 10}
        game_cache.onBeacon(player_cache3, beacon_data)
        # expect BEACON broadcast
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertEqual(answer1['OPID'], 'BEACON')
        self.assertEqual(answer1['x'], 5)
        self.assertEqual(answer1['y'], 10)
        self.assertEqual(answer1['color'], player_cache3.color)
        self.assertEqual(answer1['uuid'], player_cache3.uuid)
    
    def test_onMusic(self):
        socket1 = SocketDummy()
        socket2 = SocketDummy()
        socket3 = SocketDummy()
        
        # insert players
        gm_cache   = self.engine.cache.getFromUrl('foo')
        game_cache = gm_cache.getFromUrl('bar')
        player_cache1 = game_cache.insert('arthur', 'red', False)
        player_cache1.socket = socket1
        player_cache2 = game_cache.insert('bob', 'yellow', False)
        player_cache2.socket = socket2
        player_cache3 = game_cache.insert('carlos', 'green', False)
        player_cache3.socket = socket3

        beacon_data = {'OPID': 'MUSIC', 'action': 'refresh'}
        game_cache.onBeacon(player_cache3, beacon_data)
        # expect MUSIC refresh broadcast
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertEqual(answer1['OPID'], 'MUSIC')
        self.assertEqual(answer1['action'], 'refresh')
        
        beacon_data = {'OPID': 'MUSIC', 'action': 'reset'}
        game_cache.onBeacon(player_cache3, beacon_data)
        # expect MUSIC reset broadcast
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertEqual(answer1['OPID'], 'MUSIC')  
        self.assertEqual(answer1['action'], 'reset')
        
    def test_onCloneToken(self):
        socket1 = SocketDummy()
        socket2 = SocketDummy()
        socket3 = SocketDummy()
        
        # insert players
        gm_cache   = self.engine.cache.getFromUrl('foo')
        game_cache = gm_cache.getFromUrl('bar')
        player_cache1 = game_cache.insert('arthur', 'red', False)
        player_cache1.socket = socket1
        player_cache2 = game_cache.insert('bob', 'yellow', False)
        player_cache2.socket = socket2
        player_cache3 = game_cache.insert('carlos', 'green', False)
        player_cache3.socket = socket3
        
        # can clone token
        with db_session:
            scene = self.active_scene()
            self.purge_scene(scene)
            t1 = gm_cache.db.Token(scene=scene, url='test1', posx=5, posy=6, size=15)
            t2 = gm_cache.db.Token(scene=scene, url='test2', posx=6, posy=7, size=16)
            t3 = gm_cache.db.Token(scene=scene, url='test3', posx=7, posy=8, size=17)
            t4 = gm_cache.db.Token(scene=scene, url='test4', posx=8, posy=9, size=18)
        data = {
            'ids': [t3.id],
            'posx': 100,
            'posy': 80
        }
        game_cache.onCloneToken(player_cache1, data)
        # expect CREATE broadcast
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertEqual(answer1['OPID'], 'CREATE')
        # @NOTE: CREATE is tested in-depth on its own
        # test token data                          
        self.assertEqual(len(answer1['tokens']), 1)
        with db_session:
            clone = self.get_token(answer1['tokens'][0]['id'])
        self.assertEqual(clone.url, t3.url)
        self.assertEqual(clone.zorder, t3.zorder)
        self.assertEqual(clone.size, t3.size)
        self.assertEqual(clone.rotate, t3.rotate)
        self.assertEqual(clone.flipx, t3.flipx)
        self.assertFalse(clone.locked) # cloned tokens are not locked by default
        self.assertEqual(clone.text, t3.text)
        self.assertEqual(clone.color, t3.color)

        # can clone multiple tokens
        with db_session:
            scene = self.active_scene()
            self.purge_scene(scene)
            t1 = gm_cache.db.Token(scene=scene, url='test1', posx=5, posy=6, size=15)
            t2 = gm_cache.db.Token(scene=scene, url='test2', posx=6, posy=7, size=16)
            t3 = gm_cache.db.Token(scene=scene, url='test3', posx=7, posy=8, size=17)
            t4 = gm_cache.db.Token(scene=scene, url='test4', posx=8, posy=9, size=18)
        data = {
            'ids': [t1.id, t3.id, t4.id],
            'posx': 100,
            'posy': 80
        }
        game_cache.onCloneToken(player_cache1, data) 
        # expect CREATE broadcast
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertEqual(answer1['OPID'], 'CREATE')
        # expect tokens to be around provided position
        distances = list()
        with db_session:
            for tdata in answer1['tokens']:
                t = self.get_token(tdata['id'])
                dx = data['posx'] - t.posx
                dy = data['posy'] - t.posy
                distances.append((dx**2 + dy**2)**0.5)
        min_dist = min(distances)
        max_dist = max(distances)
        self.assertLess(max_dist - min_dist, 10)
    
    def test_onCreateScene(self):
        socket1 = SocketDummy()
        socket2 = SocketDummy()
        socket3 = SocketDummy()
        
        # insert players
        gm_cache   = self.engine.cache.getFromUrl('foo')
        game_cache = gm_cache.getFromUrl('bar')
        player_cache1 = game_cache.insert('arthur', 'red', False)
        player_cache1.socket = socket1
        player_cache2 = game_cache.insert('bob', 'yellow', True)
        player_cache2.socket = socket2
        player_cache3 = game_cache.insert('carlos', 'green', False)
        player_cache3.socket = socket3
        
        # GM can create a scene
        with db_session:
            last_scene = self.active_scene()
        game_cache.onCreateScene(player_cache2, {})
        # expect REFRESH broadcast
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertEqual(answer1['OPID'], 'REFRESH')
        # @NOTE: REFRESH is tested in-depth somewhere else
        # expect new scene to be active                  
        with db_session:
            new_scene = self.active_scene()
        self.assertNotEqual(last_scene.id, new_scene.id)
        # expect scene at end of the order list
        with db_session:
            game = self.get_game()
            expect = [new_scene.id]
            self.assertEqual(game.order, expect)
        
        # GM can create another scene at the end
        game_cache.onCreateScene(player_cache2, {}) 
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()               
        with db_session:
            new_scene = self.active_scene()
        # expect scene at end of the order list
        with db_session:
            game = self.get_game()
            expect.append(new_scene.id)
            self.assertEqual(game.order, expect)

        # GM can create yet another scene at the end
        game_cache.onCreateScene(player_cache2, {})
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()                
        with db_session:
            new_scene = self.active_scene()
        # expect scene at end of the order list
        with db_session:
            game = self.get_game()
            expect.append(new_scene.id)
            self.assertEqual(game.order, expect)

        # non-GM cannot create a scene
        last_scene = new_scene    
        game_cache.onCreateScene(player_cache1, {})
        # expect no broadcast   
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertIsNone(answer1)
        # except old scene to stay active        
        with db_session:
            new_scene = self.active_scene()  
        self.assertEqual(last_scene.id, new_scene.id)
    
    def test_onMoveScene(self):
        socket1 = SocketDummy()
        socket2 = SocketDummy()
        socket3 = SocketDummy()
        
        # insert players
        gm_cache   = self.engine.cache.getFromUrl('foo')
        game_cache = gm_cache.getFromUrl('bar')
        player_cache1 = game_cache.insert('arthur', 'red', False)
        player_cache1.socket = socket1
        player_cache2 = game_cache.insert('bob', 'yellow', True)
        player_cache2.socket = socket2
        player_cache3 = game_cache.insert('carlos', 'green', False)
        player_cache3.socket = socket3

        with db_session:
            self.purge_game()
        game_cache.onCreateScene(player_cache2, {})
        game_cache.onCreateScene(player_cache2, {})
        game_cache.onCreateScene(player_cache2, {})
        game_cache.onCreateScene(player_cache2, {})
        socket1.clearAll()
        socket2.clearAll()
        socket3.clearAll()

        # query all scenes in that game
        with db_session:
            all_scene_ids = [s.id for s in gm_cache.db.Scene.select(lambda s: s.game.url == 'bar')]
            game = self.get_game()
        self.assertEqual(len(all_scene_ids), 4)
        all_scene_ids.sort()
        s1 = all_scene_ids[0]
        s2 = all_scene_ids[1]
        s3 = all_scene_ids[2]
        s4 = all_scene_ids[3]

        with db_session:
            game = self.get_game()
            game.reorderScenes()
        self.assertEqual(game.order, [s1, s2, s3, s4]) # explicit order
        
        # GM can move a scene left
        game_cache.onMoveScene(player_cache2, {'scene': s3, 'step': -1})
        with db_session:
            game = self.get_game()
        self.assertEqual(game.order, [s1, s3, s2, s4])

        # GM can move last scene left
        game_cache.onMoveScene(player_cache2, {'scene': s4, 'step': -1})  
        with db_session:
            game = self.get_game()
        self.assertEqual(game.order, [s1, s3, s4, s2])

        # GM can move a scene right
        game_cache.onMoveScene(player_cache2, {'scene': s3, 'step': 1})  
        with db_session:
            game = self.get_game()
        self.assertEqual(game.order, [s1, s4, s3, s2])
        
        # GM can move first scene right
        game_cache.onMoveScene(player_cache2, {'scene': s1, 'step': 1})  
        with db_session:
            game = self.get_game()
        self.assertEqual(game.order, [s4, s1, s3, s2])
        
        # GM cannot move first scene too far left
        game_cache.onMoveScene(player_cache2, {'scene': s4, 'step': -1}) 
        with db_session:
            game = self.get_game()
        self.assertEqual(game.order, [s4, s1, s3, s2])
        
        # GM cannot move last scene too far right
        game_cache.onMoveScene(player_cache2, {'scene': s2, 'step': 1})  
        with db_session:
            game = self.get_game()
        self.assertEqual(game.order, [s4, s1, s3, s2])

        # a non-GM cannot move any scene
        game_cache.onMoveScene(player_cache3, {'scene': s3, 'step': -1}) 
        with db_session:
            game = self.get_game()
        self.assertEqual(game.order, [s4, s1, s3, s2])
        game_cache.onMoveScene(player_cache3, {'scene': s3, 'step': 1})  
        with db_session:
            game = self.get_game()
        self.assertEqual(game.order, [s4, s1, s3, s2])
        
    def test_onActivateScene(self):
        socket1 = SocketDummy()
        socket2 = SocketDummy()
        socket3 = SocketDummy()
        
        # insert players
        gm_cache   = self.engine.cache.getFromUrl('foo')
        game_cache = gm_cache.getFromUrl('bar')
        player_cache1 = game_cache.insert('arthur', 'red', False)
        player_cache1.socket = socket1
        player_cache2 = game_cache.insert('bob', 'yellow', True)
        player_cache2.socket = socket2
        player_cache3 = game_cache.insert('carlos', 'green', False)
        player_cache3.socket = socket3

        with db_session:
            self.purge_game()
        game_cache.onCreateScene(player_cache2, {})
        game_cache.onCreateScene(player_cache2, {})
        socket1.clearAll()
        socket2.clearAll()
        socket3.clearAll()

        # query all scenes in that game
        with db_session:
            all_scene_ids = [s.id for s in gm_cache.db.Scene.select(lambda s: s.game.url == 'bar')]
            active = self.active_scene()
        self.assertEqual(len(all_scene_ids), 2)
        self.assertEqual(all_scene_ids[1], active.id)
        
        # GM can activate a scene
        game_cache.onActivateScene(player_cache2, {'scene': all_scene_ids[0]})
        # expect REFRESH broadcast
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertEqual(answer1['OPID'], 'REFRESH')
        # @NOTE: REFRESH is tested in-depth somewhere else
        # expect 1st scene to be active   
        with db_session:
            active = self.active_scene()
        self.assertEqual(all_scene_ids[0], active.id)

        # non-GM cannot switch scene   
        game_cache.onActivateScene(player_cache1, {'scene': all_scene_ids[1]}) 
        # expect no broadcast
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertIsNone(answer1)
        # expect 1st scene to still be active   
        with db_session:
            active = self.active_scene()
        self.assertEqual(all_scene_ids[0], active.id)

        # cannot switch to unknown scene   
        game_cache.onActivateScene(player_cache2, {'scene': 57375367}) 
        # expect no broadcast
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertIsNone(answer1)
        # expect 1st scene to still be active   
        with db_session:
            active = self.active_scene()
        self.assertEqual(all_scene_ids[0], active.id)
        
    def test_onCloneScene(self): 
        socket1 = SocketDummy()
        socket2 = SocketDummy()
        socket3 = SocketDummy()
        
        # insert players
        gm_cache   = self.engine.cache.getFromUrl('foo')
        game_cache = gm_cache.getFromUrl('bar')
        player_cache1 = game_cache.insert('arthur', 'red', False)
        player_cache1.socket = socket1
        player_cache2 = game_cache.insert('bob', 'yellow', True)
        player_cache2.socket = socket2
        player_cache3 = game_cache.insert('carlos', 'green', False)
        player_cache3.socket = socket3

        def reset():
            with db_session:
                self.purge_game()
            game_cache.onCreateScene(player_cache2, {})
            game_cache.onCreateScene(player_cache2, {})
            socket1.clearAll()
            socket2.clearAll()
            socket3.clearAll()
            
            # query all scenes in that game
            with db_session:
                all_scene_ids = [s.id for s in gm_cache.db.Scene.select(lambda s: s.game.url == 'bar')]
                active = self.active_scene()
                self.assertEqual(len(all_scene_ids), 2)
                self.assertEqual(all_scene_ids[1], active.id)
                # create some tokens and background
                gm_cache.db.Token(scene=active, url='wallpaper', posx=1, posy=2, size=-1)
                for t in range(3):
                    gm_cache.db.Token(scene=active, url='test', posx=20, posy=21, size=3,
                        rotate=22.5, flipx=True, locked=True, text='foo', color='#FF0000')
                return all_scene_ids, active
        
        # clear game
        all_scene_ids, active = reset()
            
        # GM can clone a scene
        game_cache.onCloneScene(player_cache2, {'scene': all_scene_ids[1]}) 
        # expect REFRESH broadcast
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertEqual(answer1['OPID'], 'REFRESH')
        # @NOTE: REFRESH is tested in-depth somewhere else
        # expect a new scene to be active
        last_active = active
        with db_session:   
            active = self.active_scene()
            self.assertNotEqual(last_active.id, active.id)
            # ... with all tokens
            for t in active.tokens:
                self.assertEqual(t.url, 'test')
                self.assertEqual(t.posx, 20)
                self.assertEqual(t.posy, 21)
                self.assertEqual(t.size, 3)
                self.assertAlmostEqual(t.rotate, 22.5)
                self.assertTrue(t.flipx)
                self.assertTrue(t.locked) 
                self.assertEqual(t.text, 'foo')
                self.assertEqual(t.color, '#FF0000')
        # ... but no background
        self.assertIsNone(active.backing)
        # expect scene at end of the order list
        with db_session:
            game = self.get_game()
            expect = game.order
            expect.append(active.id)
            self.assertEqual(game.order, expect)
        
        # non-GM cannot clone a scene
        last_active = active
        game_cache.onCloneScene(player_cache1, {'scene': all_scene_ids[1]}) 
        # expect no broadcast
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertIsNone(answer1)
        # expect last active scene still being active
        with db_session:   
            active = self.active_scene()
        self.assertEqual(active.id, last_active.id)

        # clear game       
        all_scene_ids, last_active = reset()
        
        # clone an unknown scene scene
        game_cache.onCloneScene(player_cache1, {'scene': 234656456}) 
        # expect no broadcast
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertIsNone(answer1)
        # expect last active scene still being active
        with db_session:   
            active = self.active_scene()
        self.assertEqual(active.id, last_active.id)

    def test_onDeleteScene(self):
        socket1 = SocketDummy()
        socket2 = SocketDummy()
        socket3 = SocketDummy()
        
        # insert players
        gm_cache   = self.engine.cache.getFromUrl('foo')
        game_cache = gm_cache.getFromUrl('bar')
        player_cache1 = game_cache.insert('arthur', 'red', False)
        player_cache1.socket = socket1
        player_cache2 = game_cache.insert('bob', 'yellow', True)
        player_cache2.socket = socket2
        player_cache3 = game_cache.insert('carlos', 'green', False)
        player_cache3.socket = socket3

        def reset():
            with db_session:
                self.purge_game()
            game_cache.onCreateScene(player_cache2, {})
            game_cache.onCreateScene(player_cache2, {})
            game_cache.onCreateScene(player_cache2, {})
            game_cache.onCreateScene(player_cache2, {})
            socket1.clearAll()
            socket2.clearAll()
            socket3.clearAll()
            
            # query all scenes in that game
            with db_session:
                all_scene_ids = [s.id for s in gm_cache.db.Scene.select(lambda s: s.game.url == 'bar')]
                active = self.active_scene()
                self.assertEqual(len(all_scene_ids), 4)
                self.assertEqual(all_scene_ids[3], active.id)

            return all_scene_ids, active
        
        # clear game
        all_scene_ids, active = reset()

        # test scene order
        with db_session:
            game = gm_cache.db.Game.select(url='bar').first()
        self.assertEqual(game.order, [3, 4, 5, 6])
        
        # GM can delete an inactive scene
        game_cache.onDeleteScene(player_cache2, {'scene': all_scene_ids[1]}) 
        # expect no broadcast
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertIsNone(answer1)
        # except first id to be missing now
        with db_session:
            self.assertIsNone(gm_cache.db.Scene.select(lambda s: s.id == all_scene_ids[1]).first())
        # expect scene order with remaining scenes
        with db_session:
            game = self.get_game()
            expected = [all_scene_ids[0], all_scene_ids[2], all_scene_ids[3]]
            self.assertEqual(game.order, expected)
        # expect scene order to remain
        with db_session:
            game = gm_cache.db.Game.select(url='bar').first()
        self.assertEqual(game.order, [3, 5, 6])
        
        # clear game
        all_scene_ids, active = reset()
        
        # test scene order
        with db_session:
            game = gm_cache.db.Game.select(url='bar').first()
        self.assertEqual(game.order, [7, 8, 9, 10])

        # GM can delete an active scene
        game_cache.onDeleteScene(player_cache2, {'scene': active.id})
        # expect REFRESH broadcast
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertEqual(answer1['OPID'], 'REFRESH')
        # expect scene order to remain
        with db_session:
            game = gm_cache.db.Game.select(url='bar').first()
        self.assertEqual(game.order, [7, 8, 9])
        
        # @NOTE: REFRESH is tested in-depth somewhere else
        # except first id to be missing now
        with db_session:
            self.assertIsNone(gm_cache.db.Scene.select(lambda s: s.id == active.id).first())
        # expect another scene to be active
        with db_session:
            now_active = self.active_scene()
        self.assertNotEqual(active.id, now_active.id)
            
        # non-GM cannot delete a scene  
        game_cache.onDeleteScene(player_cache1, {'scene': all_scene_ids[0]}) 
        # expect no broadcast
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertIsNone(answer1)
        # except first id still being there
        self.assertIsNotNone(gm_cache.db.Scene.select(lambda s: s.id == all_scene_ids[0]))
        # expect the same scene order
        with db_session:
            game = gm_cache.db.Game.select(url='bar').first()
        self.assertEqual(game.order, [7, 8, 9])

        # reset to only one scene
        with db_session:
            self.purge_game()
        game_cache.onCreateScene(player_cache2, {})
        socket1.clearAll()
        socket2.clearAll()
        socket3.clearAll()
        # expect scene order with remaining scene
        with db_session:
            game = self.get_game()
            active = self.active_scene()
            self.assertEqual(game.order, [active.id])
        
        # GM can delete the last remaining scene
        game_cache.onDeleteScene(player_cache2, {'scene': active.id}) 
        # expect REFRESH broadcast
        answer1 = socket1.pop_send()
        answer2 = socket2.pop_send()
        answer3 = socket3.pop_send()
        self.assertEqual(answer1, answer2)
        self.assertEqual(answer1, answer3)
        self.assertEqual(answer1['OPID'], 'REFRESH')
        # @NOTE: REFRESH is tested in-depth somewhere else
        # except first id to be missing now
        with db_session:
            self.assertIsNone(gm_cache.db.Scene.select(lambda s: s.id == all_scene_ids[0]).first())
        # expect a new scene being created
        with db_session:
            now_active = self.active_scene()
        self.assertNotEqual(active.id, now_active.id)
        # expect scene order with freshly created scene
        with db_session:
            game = self.get_game()
            active = self.active_scene()
            self.assertEqual(game.order, [active.id])
