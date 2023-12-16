"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2022 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

import json
import httpx

from .common import Notifier


class DiscordWebhookNotifier(Notifier):
    """Send notifications to a discord webhook"""

    def __init__(self, engine, **data):
        self.engine = engine
        self.appname = data['appname']
        self.alias = data['alias']
        self.url = data['url']
        self.roles = data['roles']
        self.users = data['users']

    def get_mentions(self) -> str:
        """Get mentioning string for relevant roles and users."""
        roles = [f'<@&{role}>' for role in self.roles]
        users = [f'<@{user}>' for user in self.users]
        return f' '.join(roles + users)

    def send(self, message: str) -> None:
        content = f'{self.get_mentions()}: {message}'
        httpx.post(self.url, json={'username': self.alias, 'content': content})

    def onStart(self):
        msg = f'The VTT server {self.appname}/{self.engine.title} on {self.engine.getDomain()} is now online!'
        self.send(msg)

    def onCleanup(self, report):
        report = json.dumps(report, indent=4)
        msg = f'The VTT Server finished cleanup.\n```{report}```'
        self.send(msg)

    def onError(self, error_id, message):
        self.send(message)

