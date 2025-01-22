"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

import typing


SUPPORTED_APIS: list[str] = {
    'discord'
}


class Notifier(typing.Protocol):
    def login(self) -> None: ...
    def on_start(self) -> None: ...
    def on_cleanup(self, report: any) -> None: ...
    def on_error(self, error_id: str, message: str) -> None: ...


def parse_webhook_data(api_name: str, data: dict) -> dict | None:
    """Try to parse provider data from a dict (e.g. os.environ)."""
    url_key = f'VTT_WEBHOOK_{api_name.upper()}_URL'
    user_key = f'VTT_WEBHOOK_{api_name.upper()}_USER'

    if url_key not in data or user_key not in data:
        # API not provided
        return None
    
    return {
        'url': data[url_key],
        'users': [data[user_key]]
    }
