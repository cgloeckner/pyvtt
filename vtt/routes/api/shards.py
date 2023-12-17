"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

import flag
import requests

from bottle import *


def register(engine):
    @get('/vtt/query/<index:int>')
    def status_query(index):
        if len(engine.shards) == 0:
            abort(404)

        # ask server
        try:
            host = engine.shards[index]
        except IndexError:
            abort(404)

        data = dict()
        data['games'] = None
        data['flag'] = None
        data['build'] = {}
        try:
            json = requests.get(host + '/vtt/api/build', timeout=3).json()
            data['build'] = json
        except Exception as e:
            engine.logging.error('Server {0} seems to be offline'.format(host))

        # query server location (if possible)
        ip = host.split('://')[1].split(':')[0]
        country = engine.get_country_from_ip(ip)
        if country not in ['?', 'unknown']:
            data['flag'] = flag.flag(country)

        # query server data
        try:
            json = requests.get(host + '/vtt/api/users', timeout=3).json()
            data['games'] = json['games']['running']
        except Exception as e:
            engine.logging.error('Server {0} seems to be offline'.format(host))

        return data

    @get('/vtt/shard')
    @view('shard')
    def shard_list():
        if len(engine.shards) == 0:
            abort(404)

        return dict(engine=engine, own=engine.get_url())

