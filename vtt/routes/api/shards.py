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


def register(engine: any):

    @get('/vtt/query/<index:int>')
    def status_query(index: int):
        if len(engine.shards) == 0:
            abort(404)

        # ask server
        game_host = ''
        try:
            game_host = engine.shards[index]
        except IndexError:
            abort(404)

        data = dict()
        data['games'] = None
        data['flag'] = None
        data['build'] = {}
        try:
            json = requests.get(f'{game_host}/vtt/api/build', timeout=3).json()
            data['build'] = json
        except requests.exceptions.RequestException:
            engine.logging.error(f'Server {game_host} seems to be offline')

        # query server location (if possible)
        ip = game_host.split('://')[1].split(':')[0]
        country = engine.get_country_from_ip(ip)
        if country not in ['?', 'unknown']:
            data['flag'] = flag.flag(country)

        # query server data
        try:
            json = requests.get(f'{game_host}/vtt/api/users', timeout=3).json()
            data['games'] = json['games']['running']
        except requests.exceptions.RequestException:
            engine.logging.error(f'Server {game_host} seems to be offline')

        return data

    @get('/vtt/shard')
    @view('shard')
    def shard_list():
        if len(engine.shards) == 0:
            abort(404)

        return dict(engine=engine, own=engine.get_url())
