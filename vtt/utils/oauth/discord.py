"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import requests

import bottle

from .common import BaseLoginApi, LoginClient, Session


class DiscordLogin(BaseLoginApi):

    def __init__(self, engine: any, client: LoginClient, **data):
        super().__init__('discord', engine, **data)
        self.client = client
        self.scopes = '+'.join(['identify', 'email'])

    def get_auth_url(self) -> str:
        return (f'https://discord.com/oauth2/authorize?'
                f'client_id={self.client_id}&'
                f'redirect_uri={self.callback}&'
                f'scope={self.scopes}&'
                f'response_type=code')

    def get_session(self, request: bottle.Request) -> Session:
        code = request.url.split('code=')[1].split('&')[0]

        # query access token
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.callback
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        token = requests.post('https://discord.com/api/v8/oauth2/token', data=data, headers=headers).json()

        # query user data
        headers = {
            "Authorization": f'Bearer {token["access_token"]}'
        }
        user_data = requests.get('https://discordapp.com/api/users/@me', headers=headers).json()

        result = {
            'name': user_data['global_name'],
            'identity': user_data['email'],
            'metadata': f'discord-oauth2|{user_data["email"]}'
        }

        self.engine.logging.auth(result)

        return result
