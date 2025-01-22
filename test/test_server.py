"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2024 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import unittest
import tempfile
import pathlib
import socket

from vtt import server


class ServerTest(unittest.TestCase):

#    def test_get_unix_socket_listener_creates_socket_file(self) -> None:
#        with tempfile.TemporaryDirectory() as name:
#            path = pathlib.Path(name) / 'test.sock'
#            self.assertFalse(path.exists())
#
#            listener = server.get_unix_socket_listener(path)
#            self.assertTrue(path.exists())
#            self.assertIsNotNone(listener)
#
#    def test_get_unix_socket_listener_replaces(self) -> None:
#        with tempfile.TemporaryDirectory() as name:
#            path = pathlib.Path(name) / 'test.sock'
#            path.touch()
#            self.assertTrue(path.exists())
#
#            listener = server.get_unix_socket_listener(path)
#            self.assertTrue(path.exists())
#            self.assertIsNotNone(listener)

    def test_can_create_Server_based_on_host_and_port(self) -> None:
        s = server.VttServer(host='example.com', port=1234)
        self.assertIsInstance(s.listener, tuple)

#    def test_can_create_Server_via_unix_socket(self) -> None:
#        with tempfile.TemporaryDirectory() as name:
#            path = pathlib.Path(name) / 'test.sock'
#            s = server.VttServer(host='example.com', port=1234, unixsocket=path)
#            self.assertIsInstance(s.listener, socket.socket)
