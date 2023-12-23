"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

from gevent import lock

from .factory import create_login_api
from .common import LoginClient, AuthHandle


ProviderData = dict[str, dict[str, str]]  # keys api_name to dict of settings


class OAuthClient(LoginClient):
    def __init__(self, on_auth: AuthHandle, callback_url: str, providers: ProviderData):
        # register all provided login APIs
        self.apis = {api_name: create_login_api(self, on_auth, api_name, callback_url, providers[api_name])
                     for api_name in providers}

        # thread-safe structure to hold login sessions
        self.sessions: dict[str, any] = {}
        self.lock = lock.RLock()

    def load_session(self, state: str) -> any:
        """Query session via state but remove it from the cache"""
        with self.lock:
            return self.sessions.pop(state)

    def save_session(self, state: str, session: any) -> None:
        """Save session via state."""
        with self.lock:
            self.sessions[state] = session

    def parse_provider(self, data: str) -> str:
        provider = '-'.join(data.split('|')[:-1])

        # split 'oauth2'-section from provider
        for part in ['-oauth2', 'oauth2-']:
            provider = provider.replace(part, '')

        return provider.lower()

    def get_icon_url(self, api_name: str) -> str:
        return self.apis[api_name].icon_url
