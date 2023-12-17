"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import abc

import bottle


Session = dict[str, str]


# @NOTE: this class is not covered in the unit tests because it depends too much on external resources
class BaseLoginApi(abc.ABC):

    def __init__(self, api: str, engine: any, **data):
        self.api = api
        self.engine = engine
        self.callback = f'{engine.get_auth_callback_url()}/{api}'  # https://example.com/my/callback/path/api_name
        self.client_id = data['client_id']  # ID of API key
        self.client_secret = data['client_secret']  # Secret of API key
        self.icon_url = data['icon']

        self.login_caption = f'Login with {api}'

    def get_auth_url(self) -> str: ...
    def get_session(self, request: bottle.Request) -> Session: ...


class LoginClient(abc.ABC):
    def load_session(self, state: str) -> any: ...
    def save_session(self, state: str, session: any) -> None: ...
    def parse_provider(self, data: str) -> str: ...
    def get_icon_url(self, key: str) -> str: ...
