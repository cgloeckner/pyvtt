"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
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


class PlayerCache:
    """Holds a single player.
    """
    instance_count = 0  # instance counter for server status

    def __init__(self, engine: any, parent: any, name: str, color: str, is_gm: bool) -> None:
        PlayerCache.instance_count += 1

        self.engine = engine
        self.parent = parent  # parent cache object
        self.name = name
        self.color = color
        self.uuid = uuid.uuid4().hex  # used for HTML DOM id
        self.selected = list()
        self.index = parent.get_next_id()  # used for ordering players in the UI
        self.is_gm = is_gm  # whether this player is the GM or not
        self.timeid = time.time()  # NOTE: currently not used but could be useful later

        self.greenlet = None

        # fetch country flag from ip
        self.ip = self.engine.get_client_ip(request)
        self.country = self.engine.get_country_from_ip(self.ip)
        self.agent = self.engine.get_client_agent(request)
        # ? = localhost, 'unknown' = unittest
        self.flag = flag.flag(self.country) if self.country not in ['?', 'unknown'] else ''

        # add login to stats
        login_data = [time.time(), self.country, self.ip, self.agent]
        self.engine.logging.logins(json.dumps(login_data))

        self.lock = lock.RLock()
        self.socket = None

        self.dispatch_map = {
            'PING': self.parent.on_ping,
            'ROLL': self.parent.on_roll,
            'SELECT': self.parent.on_select,
            'RANGE': self.parent.on_range,
            'ORDER': self.parent.on_order,
            'UPDATE': self.parent.on_update_token,
            'CREATE': self.parent.on_create_token,
            'CLONE': self.parent.on_clone_token,
            'DELETE': self.parent.on_delete_token,
            'BEACON': self.parent.on_beacon,
            'MUSIC': self.parent.on_music,
            'GM-CREATE': self.parent.on_create_scene,
            'GM-MOVE': self.parent.on_move_scene,
            'GM-ACTIVATE': self.parent.on_activate_scene,
            'GM-CLONE': self.parent.on_clone_scene,
            'GM-DELETE': self.parent.on_delete_scene
        }

    def __del__(self):
        PlayerCache.instance_count -= 1

    # --- websocket implementation ------------------------------------

    def get_meta_data(self) -> dict:
        return {
            'name': self.name,
            'is_gm': self.is_gm,
            'game': self.parent.url,
            'gm': self.parent.parent.url
        }

    def is_online(self) -> bool:
        """ Returns if socket is ok. """
        return self.socket is not None and not self.socket.closed

    def read(self) -> any:
        """ Return JSON object read from socket. """
        # fetch data
        # with self.lock:# note: atm deadlocking
        raw = self.socket.receive()
        if raw is not None:
            # parse data
            return json.loads(raw)

    def write(self, data: any):
        """ Write JSON object to socket. """
        # dump data
        raw = json.dumps(data)
        # send data
        # with self.lock: # note: atm deadlocking
        if self.socket is not None:
            self.socket.send(raw)

    def fetch(self, data: dict, key: any) -> any:
        """ Try to fetch key from data or raise ProtocolError. """
        try:
            return data[key]
        except KeyError as e:
            self.socket = None
            # reraise since it's unexpected
            raise

    def handle_async(self) -> None:
        """ Runs a greenlet to handle asyncronously. """
        self.greenlet = gevent.Greenlet(run=self.handle)
        self.greenlet.start()

    def handle(self) -> None:
        """ Thread-handle for dispatching player actions. """
        try:
            while self.is_online():
                # query data and operation id
                data = self.read()

                if data is None:
                    break

                # dispatch operation
                op_id = self.fetch(data, 'OPID')
                func = self.dispatch_map[op_id]
                func(self, data)

        except Exception as error:
            self.engine.logging.warning('WebSocket died: {0}'.format(error))
            self.socket = None

        # remove player
        self.parent.logout(self)
