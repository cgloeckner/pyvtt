"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2022 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

import os

import bottle

from gevent.pywsgi import WSGIServer
from gevent import socket
from geventwebsocket.handler import WebSocketHandler


def get_unix_socket_listener(filename) -> socket.socket:
    if os.path.exists(filename):
        os.remove(filename)
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listener.bind(filename)
    listener.listen(1)
    return listener


# Server adapter providing support for WebSockets and UnixSocket
class VttServer(bottle.ServerAdapter):
    
    def __init__(self, host, port, **options):
        self.listener = (host, port)

        unixsocket = options.pop('unixsocket', '')
        if unixsocket != '':
            self.listener = get_unix_socket_listener(unixsocket)
            print('Listening on unixsocket: {0}'.format(unixsocket))

        # create ServerAdapter
        super().__init__(host, port, **options)
    
    def run(self, handler):
        server = WSGIServer(self.listener, handler, handler_class=WebSocketHandler, **self.options)
        server.serve_forever()
