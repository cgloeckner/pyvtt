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


def get_icon_url(api_name: str) -> str:
    """Return url to the service's icon."""
    if api_name == 'google':
        return 'https://www.google.com/favicon.ico'

    if api_name == 'discord':
        return 'https://assets-global.website-files.com/6257adef93867e50d84d30e2/6266bc493fb42d4e27bb8393_847541504914fd33810e70a0ea73177e.ico'

    raise NotImplementedError(f'{api_name} is not supported as OAuth mechanism')


def parse_provider_data(api_name: str, data: dict) -> dict | None:
    """Try to parse provider data from a dict (e.g. os.environ)."""
    id_key = f'VTT_OAUTH_{api_name.upper()}_ID'
    secret_key = f'VTT_OAUTH_{api_name.upper()}_SECRET'

    if id_key not in data or secret_key not in data:
        # API not provided
        return None
    
    return {
        'client_id': data[id_key],
        'client_secret': data[secret_key],
        'icon_url': get_icon_url(api_name)
    }
