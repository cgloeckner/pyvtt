"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import abc
import typing


AuthSession = dict[str, str]
AuthHandle = typing.Callable[[AuthSession], None]


# @NOTE: this class is not covered in the unit tests because it depends too much on external resources
class BaseLoginApi(abc.ABC):

    def __init__(self, api_name: str, callback_url: str, client_id: str, client_secret: str, icon_url: str):
        self.api_name = api_name
        self.callback = f'{callback_url}/{api_name}'  # https://example.com/my/callback/path/api_name
        self.client_id = client_id
        self.client_secret = client_secret
        self.icon_url = icon_url

        self.login_caption = f'Login with {api_name}'

    def get_auth_url(self) -> str: ...
    def get_session(self, request_url: str) -> AuthSession: ...


class LoginClient(abc.ABC):
    def load_session(self, state: str) -> any: ...
    def save_session(self, state: str, session: any) -> None: ...
    def parse_provider(self, data: str) -> str: ...
    def get_icon_url(self, key: str) -> str: ...
