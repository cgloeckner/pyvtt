"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2022 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

import json
import time
import uuid

import flag
import gevent
from bottle import request
from gevent import lock


class PlayerCache(object):
    """Holds a single player.
    """
    instance_count = 0  # instance counter for server status

    def __init__(self, engine, parent, name, color, is_gm):
        PlayerCache.instance_count += 1

        self.engine = engine
        self.parent = parent  # parent cache object
        self.name = name
        self.color = color
        self.uuid = uuid.uuid4().hex  # used for HTML DOM id
        self.selected = list()
        self.index = parent.getNextId()  # used for ordering players in the UI
        self.is_gm = is_gm  # whether this player is the GM or not
        self.timeid = time.time()  # NOTE: currently not used but could be useful later

        self.greenlet = None

        # fetch country flag from ip
        self.ip = self.engine.getClientIp(request)
        self.country = self.engine.getCountryFromIp(self.ip)
        self.agent = self.engine.getClientAgent(request)
        # ? = localhost, 'unknown' = unittest
        self.flag = flag.flag(self.country) if self.country not in ['?', 'unknown'] else ''

        # add login to stats
        login_data = [time.time(), self.country, self.ip, self.agent]
        self.engine.logging.logins(json.dumps(login_data))

        self.lock = lock.RLock()
        self.socket = None

        self.dispatch_map = {
            'PING': self.parent.onPing,
            'ROLL': self.parent.onRoll,
            'SELECT': self.parent.onSelect,
            'RANGE': self.parent.onRange,
            'ORDER': self.parent.onOrder,
            'UPDATE': self.parent.onUpdateToken,
            'CREATE': self.parent.onCreateToken,
            'CLONE': self.parent.onCloneToken,
            'DELETE': self.parent.onDeleteToken,
            'BEACON': self.parent.onBeacon,
            'MUSIC': self.parent.onMusic,
            'GM-CREATE': self.parent.onCreateScene,
            'GM-MOVE': self.parent.onMoveScene,
            'GM-ACTIVATE': self.parent.onActivateScene,
            'GM-CLONE': self.parent.onCloneScene,
            'GM-DELETE': self.parent.onDeleteScene
        }

    def __del__(self):
        PlayerCache.instance_count -= 1

    # --- websocket implementation ------------------------------------

    def getMetaData(self):
        return {
            'name': self.name,
            'is_gm': self.is_gm,
            'game': self.parent.url,
            'gm': self.parent.parent.url
        }

    def isOnline(self):
        """ Returns if socket is ok. """
        return self.socket is not None and not self.socket.closed

    def read(self):
        """ Return JSON object read from socket. """
        # fetch data
        # with self.lock:# note: atm deadlocking
        raw = self.socket.receive()
        if raw is not None:
            # parse data
            return json.loads(raw)

    def write(self, data):
        """ Write JSON object to socket. """
        # dump data
        raw = json.dumps(data)
        # send data
        # with self.lock: # note: atm deadlocking
        if self.socket is not None:
            self.socket.send(raw)

    def fetch(self, data, key):
        """ Try to fetch key from data or raise ProtocolError. """
        try:
            return data[key]
        except KeyError as e:
            self.socket = None
            # reraise since it's unexpected
            raise

    def handle_async(self):
        """ Runs a greenlet to handle asyncronously. """
        self.greenlet = gevent.Greenlet(run=self.handle)
        self.greenlet.start()

    def handle(self):
        """ Thread-handle for dispatching player actions. """
        try:
            while self.isOnline():
                # query data and operation id
                data = self.read()

                if data is None:
                    break

                # dispatch operation
                opid = self.fetch(data, 'OPID')
                func = self.dispatch_map[opid]
                func(self, data)

        except Exception as error:
            self.engine.logging.warning('WebSocket died: {0}'.format(error))
            self.socket = None

        # remove player
        self.parent.logout(self)
