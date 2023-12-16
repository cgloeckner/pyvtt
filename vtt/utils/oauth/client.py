"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2022 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import base64
import json
import logging
import os
import pathlib
import random
import smtplib
import sys
import tempfile
import traceback
import uuid
import httpx
import requests
import typing
import abc

from google.oauth2 import id_token
from google_auth_oauthlib.flow import InstalledAppFlow
import google.auth.transport.requests

import bottle
from authlib.integrations.requests_client import OAuth2Session
from gevent import lock

from .google import GoogleLogin
from .discord import DiscordLogin


class OAuthLogin:
    def __init__(self, engine, **kwargs):
        self.engine = engine

        # register all oauth providers
        self.providers = {}
        for provider in kwargs['providers']:
            if provider == 'google':
                self.providers['google'] = GoogleLogin(engine, self, **kwargs['providers'][provider])
            if provider == 'discord':
                self.providers['discord'] = DiscordLogin(engine, self, **kwargs['providers'][provider])

        # thread-safe structure to hold login sessions
        self.sessions = dict()
        self.lock = lock.RLock()

    def loadSession(self, state):
        """Query session via state but remove it from the cache"""
        with self.lock:
            return self.sessions.pop(state)

    def saveSession(self, state, session):
        with self.lock:
            self.sessions[state] = session

    @staticmethod
    def parseProvider(s: str) -> str:
        provider = '-'.join(s.split('|')[:-1])

        # split 'oauth2'-section from provider
        for s in ['-oauth2', 'oauth2-']:
            provider = provider.replace(s, '')

        return provider.lower()

    def getIconUrl(self, key):
        return self.providers[key].icon_url
