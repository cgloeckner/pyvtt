"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2022 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import os

from google.oauth2 import id_token
from google_auth_oauthlib.flow import InstalledAppFlow
import google.auth.transport.requests

import bottle

from .common import BaseLoginApi


class GoogleLogin(BaseLoginApi):

    def __init__(self, engine, parent, **data):
        super().__init__('google', engine, **data)
        self.parent = parent
        self.icon_url = data['icon']

        if engine.debug:
            # accept non-https for testing oauth (e.g. localhost)
            os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    def getAuthUrl(self):
        """ Generate google-URL to access in order to fetch data. """
        # create auth flow session
        f = InstalledAppFlow.from_client_config(
            client_config={
                'web': {
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                    'token_uri': 'https://oauth2.googleapis.com/token'
                }
            },
            scopes=[
                'https://www.googleapis.com/auth/userinfo.email',
                'https://www.googleapis.com/auth/userinfo.profile',
                'openid'
            ],
            redirect_uri=self.callback)

        auth_url, state = f.authorization_url()
        self.parent.saveSession(state, f)

        return auth_url

    def getSession(self, request):
        """ Query google to return required user data and infos."""
        state = request.url.split('state=')[1].split('&')[0]

        # fetch token
        f = self.parent.loadSession(state)
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

        self.engine.logging.auth(result)

        return result
