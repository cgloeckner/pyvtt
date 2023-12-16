"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2022 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import abc


# @NOTE: this class is not covered in the unit tests because it depends too much on external resources
class BaseLoginApi(abc.ABC):

    def __init__(self, api, engine, **data):
        self.api = api
        self.engine = engine
        self.callback = f'{engine.getAuthCallbackUrl()}/{api}'  # https://example.com/my/callback/path/api_name
        self.client_id = data['client_id']  # ID of API key
        self.client_secret = data['client_secret']  # Secret of API key

        self.login_caption = f'Login with {api}'

    def getLogoutUrl(self): ...

    def getGmInfo(self, url):
        return ''
