"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import unittest

from vtt import utils
from .mock import LoginMock


class OAuthClientTest(unittest.TestCase):

    def on_auth(self, data: dict) -> None:
        self.last_auth = data

    def setUp(self) -> None:
        self.last_auth = None

        self.client = utils.OAuthClient(self.on_auth, 'http://example.com/callback', {
            'discord': {
                'client_id': '59rue6z05rue6z0bh5ez',
                'client_secret': 'nogfihbdurmhj083uzj086vuz',
                'icon_url': 'https://discord.com/icon.png'
            },
            'google': {
                'client_id': 'b5zezurv6zrz',
                'client_secret': 'se57m8d68n56ezvg4ezez',
                'icon_url': 'https://google.com/icon.png'
            }
        })

    def test_constructor(self) -> None:
        self.assertIn('discord', self.client.apis)
        self.assertIn('google', self.client.apis)

    def test_cannot_load_non_existing_session(self) -> None:
        with self.assertRaises(KeyError):
            self.client.load_session('bfnt845zbe4')

    def test_can_save_and_load_session(self) -> None:
        original = object()
        self.client.save_session('bfnt845zbe4', original)

        loaded = self.client.load_session('bfnt845zbe4')
        self.assertEqual(loaded, original)

    def test_can_overwrite_session(self) -> None:
        original = object()
        self.client.save_session('bfnt845zbe4', original)

        overwritten = object()
        self.client.save_session('bfnt845zbe4', overwritten)

        loaded = self.client.load_session('bfnt845zbe4')
        self.assertNotEqual(loaded, original)
        self.assertEqual(loaded, overwritten)

    def test_parse_provider(self) -> None:
        data = 'oauth2-SerViCe|my_name'
        provider = self.client.parse_provider(data)
        self.assertEqual(provider, 'service')

        data = 'SeRvicE-oauth2|my_name'
        provider = self.client.parse_provider(data)
        self.assertEqual(provider, 'service')

    def test_get_icon_url_works_for_supported_providers(self) -> None:
        for api_name in ['discord', 'google']:
            icon_url = self.client.get_icon_url(api_name)
            self.assertEqual(icon_url, f'https://{api_name}.com/icon.png')

    def test_cannot_get_icon_url_works_for_unsupported_provider(self) -> None:
        self.assertNotIn('foobar', self.client.apis.keys())

        with self.assertRaises(KeyError):
            self.client.get_icon_url('foobar')
