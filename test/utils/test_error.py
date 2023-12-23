"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import unittest
import bottle
import json
import webtest

from vtt import utils


class ErrorReporterTest(unittest.TestCase):

    @staticmethod
    def get_client_ip(_: bottle.Request) -> str:
        return '0.0.0.0'

    def on_error(self, error_id: str, message: str) -> None:
        self.last_error = (error_id, message)

    def setUp(self):
        self.last_error = (None, None)
        self.error_reporter = utils.ErrorDispatcher(self.get_client_ip, self.on_error)

        self.bottle_app = bottle.Bottle()
        self.bottle_app.install(self.error_reporter.plugin)
        self.bottle_app.catchall = False

        @self.bottle_app.get('/<value>')
        def index(value: str):
            if value == 'okay':
                return 'fine'
            if value == 'redirect':
                bottle.redirect('/okay')
            if value == 'quit':
                raise KeyboardInterrupt()
            if value != 'plain':
                raise Exception()

            error = NotImplementedError()
            error.metadata = {'value': value}
            raise error

        self.app = webtest.TestApp(self.bottle_app)

    def test_no_error_causes_no_report(self):
        self.app.get('/okay')

        error_id, message = self.last_error
        self.assertIsNone(error_id)
        self.assertIsNone(message)

    def test_redirect_is_not_caught(self):
        self.app.get('/redirect')

        error_id, message = self.last_error
        self.assertIsNone(error_id)
        self.assertIsNone(message)

    def test_keyboard_interrupt_is_not_caught(self):
        with self.assertRaises(KeyboardInterrupt):
            self.app.get('/quit')

        error_id, message = self.last_error
        self.assertIsNone(error_id)
        self.assertIsNone(message)

    def test_error_is_caught_without_metadata(self):
        self.app.get('/plain', expect_errors=True)

        error_id, message = self.last_error
        self.assertIsNotNone(error_id)
        self.assertIsNotNone(message)

        data = json.loads(message)
        for key in ['error_id', 'route_url', 'client_ip', 'cookies', 'metadata', 'stacktrace']:
            self.assertIn(key, data)

    def test_error_is_caught(self):
        self.app.get('/foo', expect_errors=True)

        error_id, message = self.last_error
        self.assertIsNotNone(error_id)
        self.assertIsNotNone(message)

        data = json.loads(message)
        for key in ['error_id', 'route_url', 'client_ip', 'cookies', 'metadata', 'stacktrace']:
            self.assertIn(key, data)

    def test_error_caught_while_ajax(self):
        self.app.get('/foo', xhr=True, expect_errors=True)

        error_id, message = self.last_error
        self.assertIsNotNone(error_id)
        self.assertIsNotNone(message)

        data = json.loads(message)
        for key in ['error_id', 'route_url', 'client_ip', 'cookies', 'metadata', 'stacktrace']:
            self.assertIn(key, data)
