"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import requests
import gevent

from test.common import EngineBaseTest, make_image
from vtt import routes


class ApiRoutesTest(EngineBaseTest):

    def setUp(self):
        super().setUp()
        routes.register_gm(self.engine)
        routes.register_player(self.engine)
        routes.register_resources(self.engine)
        routes.register_api(self.engine)
        # @NOTE: custom error pages are not routed here

    def test_api_get_queries(self):
        ret = self.app.get('/vtt/api/users', expect_errors=True)
        self.assertEqual(ret.status_int, 200)

        ret = self.app.get('/vtt/api/logins', expect_errors=True)
        self.assertEqual(ret.status_int, 200)

        ret = self.app.get('/vtt/api/auth', expect_errors=True)
        self.assertEqual(ret.status_int, 200)

    def test_cannot_query_games_and_assets_as_default_user(self):
        # register arthur
        ret = self.app.post('/vtt/join', {'gmname': 'arthur'}, xhr=True)
        self.assertEqual(ret.status_int, 200)

        # create a game
        img_small = make_image(512, 512)
        ret = self.app.post('/vtt/import-game/test-game-1',
                            upload_files=[('file', 'test.png', img_small)], xhr=True)
        self.assertEqual(ret.status_int, 200)
        self.app.reset()

        ret = self.app.get('/vtt/api/games-list/arthur', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

        ret = self.app.get('/vtt/api/assets-list/arthur/test-game-1', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_can_query_games_and_assets_as_gm(self):
        # register arthur
        ret = self.app.post('/vtt/join', {'gmname': 'arthur'}, xhr=True)
        self.assertEqual(ret.status_int, 200)

        # create a game
        img_small = make_image(512, 512)
        ret = self.app.post('/vtt/import-game/test-game-1', upload_files=[('file', 'test.png', img_small)], xhr=True)
        self.assertEqual(ret.status_int, 200)
        gm_sid = self.app.cookies['session']
        self.app.reset()

        # login as arthur
        self.app.set_cookie('session', gm_sid)

        ret = self.app.get('/vtt/api/games-list/arthur', expect_errors=True)
        self.assertEqual(ret.status_int, 200)

        ret = self.app.get('/vtt/api/assets-list/arthur/test-game-1', expect_errors=True)
        self.assertEqual(ret.status_int, 200)

    def test_query_this_server_if_no_shards_specified(self):
        ret = self.app.get('/vtt/query/0', expect_errors=True)
        self.assertEqual(ret.status_int, 200)

    def test_query_servers_within_shard(self):
        # setup server shards
        test_ports = [8081, 8000]
        self.engine.shards = ['http://localhost:{0}'.format(p) for p in test_ports]
        self.engine.shards.append('http://localhost:80')  # this server
        greenlets = list()
        for port in test_ports:
            # confirm port to be free
            with self.assertRaises(requests.exceptions.ConnectionError):
                requests.get('http://localhost:{0}'.format(port))
            # setup server instance
            e = EngineBaseTest()
            e.setUp()
            e.engine.hosting['port'] = port
            e.engine.shards = self.engine.shards
            # run in thread
            g = gevent.Greenlet(run=e.engine.run)
            g.start()
            greenlets.append(g)
            # confirm server is online
            requests.get('http://localhost:{0}'.format(port))

        # can query all servers
        for i, url in enumerate(self.engine.shards):
            ret = self.app.get('/vtt/query/{0}'.format(i))
            self.assertEqual(ret.status_int, 200)
            # @NOTE: cannot test countryCode due to localhost and status
            # because this may fail on the GitHub workflow test

        # stop server shard instances
        for g in greenlets:
            gevent.kill(g)

    def test_cannot_query_unknown_server(self):
        ret = self.app.get('/vtt/query/245245', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_show_shard_page_if_no_shards_specified(self):
        ret = self.app.get('/vtt/shard', expect_errors=True)
        self.assertEqual(ret.status_int, 200)

    def test_show_shard_page_if_only_one_server_specified(self):
        self.engine.shards = ['http://localhost:80']
        ret = self.app.get('/vtt/shard')
        self.assertEqual(ret.status_int, 200)

    def test_show_shard_page_if_multiple_servers_specified(self):
        self.engine.shards = ['https://{0}'.format(h) for h in ['example.com', 'foo.bar', 'test.org']]
        ret = self.app.get('/vtt/shard')
        self.assertEqual(ret.status_int, 200)
