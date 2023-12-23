"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

from vtt.utils.auth.common import LoginClient, AuthSession


class LoginMock(LoginClient):
    def __init__(self):
        self.sessions: dict[str, any] = {}

    def load_session(self, state: str) -> AuthSession:
        return self.sessions.pop(state)

    def save_session(self, state: str, session: AuthSession) -> None:
        self.sessions[state] = session

    def parse_provider(self, data: str) -> str:
        return data.lower()

    def get_icon_url(self, key: str) -> str:
        return f'http://example.com/client/{key}.png'
