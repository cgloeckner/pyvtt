"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

from .common import LoginClient, BaseLoginApi, AuthHandle
from .discord import DiscordLogin
from .google import GoogleLogin


SUPPORTED_LOGIN_APIS: dict[str, any] = {
    'google': GoogleLogin,
    'discord': DiscordLogin
}


def create_login_api(client: LoginClient, on_auth: AuthHandle, api_name: str, callback_url: str,
                     data: dict) -> BaseLoginApi:
    """Figure out Login API implementation and create an instance."""
    class_ = SUPPORTED_LOGIN_APIS[api_name]
    return class_(client=client, on_auth=on_auth, callback_url=callback_url, **data)
