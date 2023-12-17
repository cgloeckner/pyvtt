"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

from gevent import lock

from .common import LoginClient
from .discord import DiscordLogin
from .google import GoogleLogin


class OAuthLogin(LoginClient):
    def __init__(self, engine: any, **kwargs):
        self.engine = engine

        # register all oauth providers
        self.providers = {}
        for provider in kwargs['providers']:
            if provider == 'google':
                self.providers['google'] = GoogleLogin(engine, self, **kwargs['providers'][provider])
            if provider == 'discord':
                self.providers['discord'] = DiscordLogin(engine, self, **kwargs['providers'][provider])

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

    def get_icon_url(self, key: str) -> str:
        return self.providers[key].icon_url
