"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import bottle
import google.auth.transport.requests
from google.oauth2 import id_token
from google_auth_oauthlib.flow import InstalledAppFlow

from .common import BaseLoginApi, LoginClient, AuthSession, AuthHandle


class GoogleLogin(BaseLoginApi):

    def __init__(self, client: LoginClient, on_auth: AuthHandle, callback_url: str, client_id: str, client_secret: str,
                 icon_url: str):
        super().__init__('google', callback_url, client_id, client_secret, icon_url)
        self.client = client
        self.on_auth = on_auth

        self.client_config = {
            'web': {
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                    'token_uri': 'https://oauth2.googleapis.com/token'
                }
        }

        self.scopes = [f'https://www.googleapis.com/auth/{scope}' for scope in ['userinfo.email', 'userinfo.profile']]
        self.scopes.append('openid')

    def get_auth_url(self) -> str:
        """ Generate google-URL to access in order to fetch data. """
        # create auth flow session
        f = InstalledAppFlow.from_client_config(client_config=self.client_config, scopes=self.scopes,
                                                redirect_uri=self.callback)

        auth_url, state = f.authorization_url()
        self.client.save_session(state, f)

        return auth_url

    # FIXME: not tested yet, because it would requires mocking the google oauth api
    def get_session(self, request_url) -> AuthSession:
        """ Query google to return required user data and infos."""
        state = request_url.split('state=')[1].split('&')[0]

        # fetch token
        f = self.client.load_session(state)
        f.fetch_token(authorization_response=bottle.request.url)
        creds = f.credentials
        token_request = google.auth.transport.requests.Request()

        id_info = id_token.verify_oauth2_token(
            id_token=creds._id_token,
            request=token_request,
            audience=self.client_id
        )

        result = {
            'name': id_info.get('name'),
            'identity': id_info.get('email'),
            'metadata': f'google-oauth2|{id_info.get("sub")}'
        }

        self.on_auth(result)

        return result
