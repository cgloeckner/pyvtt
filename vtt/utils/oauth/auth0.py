"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2022 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import base64
import json
from authlib.integrations.requests_client import OAuth2Session

from .common import BaseLoginApi


# FIXME: deprecated implementation


# @NOTE: this class is not covered in the unit tests because it depends too much on external resources
class Auth0Api(BaseLoginApi):

    def __init__(self, engine, **data):
        super().__init__('auth0', engine, **data)
        self.login_caption   = 'Click to Login'
        self.auth_endpoint   = f'https://{data["domain"]}/authorize'
        self.logout_endpoint = f'https://{data["domain"]}/v2/logout'
        self.token_endpoint  = f'https://{data["domain"]}/oauth/token'

        self.logout_callback = engine.getUrl()

        # if engine.debug:
        #    # accept non-https for testing oauth (e.g. localhost)
        #    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    def getAuthUrl(self):
        """ Generate external oauth URL to access in order to fetch data. """
        # create session, redirect uri and state
        s = OAuth2Session(
            client_id=self.client_id,
            client_secret=self.client_secret,
            scope='openid profile email',
            redirect_uri=self.callback
        )
        uri, state = s.create_authorization_url(self.auth_endpoint)
        self.saveSession(state, s)

        return uri

    def get_logout_url(self):
        return f'{self.logout_endpoint}?client_id={self.client_id}&returnTo={self.logout_callback}'

    def getSession(self, request):
        """ Query google to return required user data and infos."""
        state = BaseLoginApi.parseStateFromUrl(request.url)

        # fetch token
        try:
            s = self.loadSession(state)
        except KeyError:
            return {}

        token = s.fetch_token(
            url=self.token_endpoint,
            authorization_response=request.url
        )

        # split ID-Token
        id_token = token['id_token']
        header, payload, signature = id_token.split('.')

        # enlarge payload with '='s
        payload += '=' * (4 - len(payload) % 4)

        # NOTE: gravatar data inside must be read urlsafe(!)
        payload = base64.urlsafe_b64decode(payload)
        data = json.loads(payload)

        # create login data
        result = {
            'name'     : data['name'],
            'identity' : data['email'],
            'metadata' : data['sub']
        }
        if 'auth0' in data['sub']:
            # split name from email login
            result['name'] = data['name'].split('@')[0]

        self.engine.logging.auth(result)

        return result

    @staticmethod
    def parseProvider(s):
        provider = '-'.join(s.split('|')[:-1])

        # split 'oauth2'-section from provider
        for s in ['-oauth2', 'oauth2-']:
            provider = provider.replace(s, '')

        return provider.lower()

