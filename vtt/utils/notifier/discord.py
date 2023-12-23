"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

import json
import httpx


class DiscordWebhook:
    """Send notifications to a discord webhook"""

    def __init__(self, app_title: str, alias: str, url: str, roles: list[str], users: list[str]):
        self.app_title = app_title

        self.alias = alias
        self.url = url
        self.roles = roles
        self.users = users

    def get_mentions(self) -> str:
        """Get mentioning string for relevant roles and users."""
        roles = [f'<@&{role}>' for role in self.roles]
        users = [f'<@{user}>' for user in self.users]
        return f' '.join(roles + users)

    def send(self, content: str) -> None:
        httpx.post(self.url, json={'username': self.alias, 'content': content})

    def on_start(self) -> None:
        msg = f'The VTT Server {self.app_title} is now online!'
        self.send(msg)

    def on_cleanup(self, report: dict) -> None:
        report = json.dumps(report, indent=4)
        msg = (f'The VTT Server finished cleanup.\n'
               f'```{report}```')
        self.send(msg)

    def on_error(self, error_id: str, message: str):
        self.send(f'{self.get_mentions()}:\n'
                  f'Exception Traceback `#{error_id}`\n'
                  f'```{message}```')
