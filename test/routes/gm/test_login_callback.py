"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2024 Christian Glöckner
License: MIT (see LICENSE for details)
"""

from urllib.parse import urlparse, parse_qs

from test.common import EngineBaseTest
from vtt import routes, orm, utils


def skip_on_auth(_: any) -> None:
    pass


class DummyProviderLogin(utils.BaseLoginApi):
    def __init__(self, client: any, on_auth: any, callback_url: str, client_id: str, client_secret: str,
                 icon_url: str):
        super().__init__('dummy', callback_url, client_id, client_secret, icon_url)
        self.client = client
        self.on_auth = on_auth
        self.scopes = '+'.join(['identify', 'email'])

    def get_auth_url(self) -> str:
        return (f'https://example.com/oauth2/authorize?'
                f'client_id={self.client_id}&'
                f'redirect_uri={self.callback}&'
                f'scope={self.scopes}&'
                f'response_type=code')

    def get_session(self, request_url: str) -> dict[str, str]:
        data = parse_qs(urlparse(request_url).query)
        return {
            'name': data['first'][0],
            'identity': data['second'][0],
            'metadata': data['third'][0]
        }


class GmLoginCallbackRoutesTest(EngineBaseTest):

    def setUp(self) -> None:
        super().setUp()

        # register dummy provider as supported
        utils.auth.SUPPORTED_LOGIN_APIS['dummy'] = DummyProviderLogin

        # configure dummy provider before registering routes
        self.engine.login_api = utils.OAuthClient(
            on_auth=skip_on_auth, callback_url=self.engine.get_auth_callback_url(),
            providers={'dummy': {
                'client_id': 'dummyfoobar',
                'client_secret': 'dummysecret',
                'icon_url': 'dummy.png'
            }}
        )

        routes.register_gm(self.engine)
        routes.register_player(self.engine)
        routes.register_resources(self.engine)
        # @NOTE: custom error pages are not routed here

    def test_can_login_via_callback_and_create_new_account(self) -> None:
        with orm.db_session:
            gm = self.engine.main_db.GM.select(lambda g: g.identity == 'foo123').first()
            self.assertIsNone(gm)

        ret = self.app.get('/vtt/callback/dummy?first=foo&second=foo123&third=bar@spam.la')
        self.assertEqual(ret.status_int, 302)
        self.assertEqual(ret.location, 'http://localhost:80/')

        sid = self.app.cookies['session']
        self.assertNotEquals(sid, '')

        with orm.db_session:
            gm = self.engine.main_db.GM.select(lambda g: g.sid == sid).first()
            self.assertIsNotNone(gm)
            self.assertEqual(gm.name, 'foo')
            self.assertEqual(gm.identity, 'foo123')
            self.assertEqual(gm.metadata, 'bar@spam.la')
            self.assertEqual(gm.sid, self.app.cookies['session'])
            gm_cache = self.engine.cache.get(gm)

        self.assertIsNotNone(gm_cache)

    def test_can_login_via_callback_to_existing_account(self) -> None:
        ret = self.app.get('/vtt/callback/dummy?first=foo&second=foo123&third=bar@spam.la')
        self.assertEqual(ret.status_int, 302)

        with orm.db_session:
            gm = self.engine.main_db.GM.select(lambda g: g.identity == 'foo123').first()
            self.assertIsNotNone(gm)

        old_sid = self.app.cookies['session']

        ret = self.app.get('/vtt/callback/dummy?first=New Name&second=foo123&third=new@mail.org')
        self.assertEqual(ret.status_int, 302)

        # expect updated data
        with orm.db_session:
            gm = self.engine.main_db.GM.select(lambda g: g.identity == 'foo123').first()
            self.assertEqual(gm.sid, self.app.cookies['session'])
            self.assertNotEqual(gm.sid, old_sid)
            self.assertEqual(gm.name, 'New Name')
            self.assertEqual(gm.identity, 'foo123')
            self.assertEqual(gm.metadata, 'new@mail.org')
