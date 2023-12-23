"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import unittest

from .mock import LoginMock
from vtt.utils.auth.factory import SUPPORTED_LOGIN_APIS, create_login_api


class AuthApiFactoryTest(unittest.TestCase):

    def mock_auth(self, _):
        pass

    def test_supported_apis(self) -> None:
        client = LoginMock()
        mock_data = {
            'client_id': '369ghrhh',
            'client_secret': '356845z09ruzn08ueg9',
            'icon_url': 'http://example.com/foo.png'
        }

        for api_name in SUPPORTED_LOGIN_APIS:
            create_login_api(client, self.mock_auth, api_name, 'http://example.com', mock_data)

    def test_unsupported_api_raises_exception(self) -> None:
        client = LoginMock()
        mock_data = {
            'client_id': '369ghrhh',
            'client_secret': '356845z09ruzn08ueg9',
            'icon_url': 'http://example.com/foo.png'
        }

        self.assertNotIn('foobar', SUPPORTED_LOGIN_APIS)

        with self.assertRaises(KeyError):
            create_login_api(client, self.mock_auth, 'foobar', 'http://example.com', mock_data)
