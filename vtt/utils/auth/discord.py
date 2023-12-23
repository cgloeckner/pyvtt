"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import requests

from .common import BaseLoginApi, LoginClient, AuthSession, AuthHandle


class DiscordLogin(BaseLoginApi):

    def __init__(self, client: LoginClient, on_auth: AuthHandle, callback_url: str, client_id: str, client_secret: str,
                 icon_url: str):
        super().__init__('discord', callback_url, client_id, client_secret, icon_url)
        self.client = client
        self.on_auth = on_auth
        self.scopes = '+'.join(['identify', 'email'])

    def get_auth_url(self) -> str:
        return (f'https://discord.com/oauth2/authorize?'
                f'client_id={self.client_id}&'
                f'redirect_uri={self.callback}&'
                f'scope={self.scopes}&'
                f'response_type=code')

    # FIXME: not tested yet, because it would requires mocking the discord oauth api
    def get_session(self, request_url: str) -> AuthSession:
        code = request_url.split('code=')[1].split('&')[0]

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

        self.on_auth(result)

        return result
