"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import json
import unittest

import httpx
import pytest

from vtt import utils


class DiscordWebhookTest(unittest.TestCase):

    def patched_httpx_post(self, url: str, **kwargs) -> None:
        self.last_post = kwargs
        self.last_post['url'] = url

    def setUp(self):
        self.last_post = None

        patch = pytest.MonkeyPatch()
        patch.setattr(httpx, 'post', self.patched_httpx_post)

        self.notifier = utils.DiscordWebhook(app_title='unittest on 0.0.0.0', alias='my_name',
                                             url='http://example.com/api', roles=['g9d8g5d56', '090lzvtwvt'],
                                             users=['alice', 'bob'])

    def test_get_mentions(self) -> None:
        dump = self.notifier.get_mentions()
        expect = f'<@&g9d8g5d56> <@&090lzvtwvt> <@alice> <@bob>'
        self.assertEqual(dump, expect)

    def test_get_mentions_without_roles(self) -> None:
        self.notifier.roles.clear()

        dump = self.notifier.get_mentions()
        expect = '<@alice> <@bob>'
        self.assertEqual(dump, expect)

    def test_get_mentions_without_users(self) -> None:
        self.notifier.users.clear()

        dump = self.notifier.get_mentions()
        expect = '<@&g9d8g5d56> <@&090lzvtwvt>'
        self.assertEqual(dump, expect)

    def test_get_mentions_without_any_handle(self) -> None:
        self.notifier.roles.clear()
        self.notifier.users.clear()

        dump = self.notifier.get_mentions()
        expect = ''
        self.assertEqual(dump, expect)

    def test_send(self) -> None:
        self.notifier.send('what a wonderful day')
        expect = {
            'url': self.notifier.url,
            'json': {
                'username': 'my_name',
                'content': 'what a wonderful day'
            }
        }
        self.assertEqual(self.last_post, expect)

    def test_on_start_has_no_mentions(self) -> None:
        self.notifier.on_start()
        expect = {
            'url': self.notifier.url,
            'json': {
                'username': 'my_name',
                'content': 'The VTT Server unittest on 0.0.0.0 is now online!'
            }
        }
        self.assertEqual(self.last_post, expect)

    def test_on_cleanup_has_no_mentions(self) -> None:
        data = {'did': 'nothing fancy'}
        self.notifier.on_cleanup(data)

        expect = {
            'url': self.notifier.url,
            'json': {
                'username': 'my_name',
                'content': 'The VTT Server finished cleanup.\n'
                           f'```{json.dumps(data, indent=4)}```'
            }
        }
        self.assertEqual(self.last_post, expect)

    def test_on_error_has_mentions(self) -> None:
        error_id = '5849bzh5408h4g'
        message = 'omg it caught fire!'
        self.notifier.on_error(error_id, message)

        expect = {
            'url': self.notifier.url,
            'json': {
                'username': 'my_name',
                'content': f'{self.notifier.get_mentions()}:\n'
                           f'Exception Traceback `#{error_id}`\n'
                           f'```{message}```'
            }
        }
        self.assertEqual(self.last_post, expect)
