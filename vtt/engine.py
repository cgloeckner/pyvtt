"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2022 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

import hashlib
import json
import os
import pathlib
import re
import requests
import shutil
import subprocess
import sys
import time
import uuid
import typing

import bottle
import atomicx

import vtt.utils as utils
from buildnumber import BuildNumber
from vtt.settings import env_settings, Settings
from vtt.cache import EngineCache
from vtt.orm.register import db_session, create_main_database
from vtt.server import VttServer


class Engine(object):

    def __init__(self, **kwargs):
        app_root = kwargs.pop("app_root", pathlib.Path("."))

        kwargs = env_settings(**kwargs)
        self.settings = Settings(**kwargs)
        
        # initialize path api
        pref_root: pathlib.Path | None = None
        if self.settings.pref_dir != "":
            pref_root = pathlib.Path(self.settings.pref_dir)
            # FIXME: path_api should work with str instead and do the
            # pathlib stuff on its own

        self.paths = utils.PathApi(
            app_name=self.settings.app_name,
            pref_root=pref_root,
            app_root=app_root
        )
        self.paths.ensure(self.paths.get_export_path())

        self.app = bottle.default_app()

        # setup per-game stuff
        self.checksums = dict()
        self.locks = dict()
        
        # webserver stuff
        self.listen = '0.0.0.0'
        self.maintenance = atomicx.AtomicInt()
        
        # blacklist for GM names and game URLs
        self.gm_blacklist = ['', 'static', 'asset', 'vtt', 'game']
        self.url_regex    = r'^[A-Za-z0-9_\-.]+$'
        
        self.playercolors = [
            '#FF0000', '#00FF00', '#0000FF', '#FFFF00',
            '#FF00FF', "#C52828", "#13AA4F", "#ECBC15",
            "#7F99C7", "#9251B7", "#797A90", "#80533F",
            "#21A0B7"]
        
        self.links = [
            {
                "label" : "HOME",
                "url"   : "/"
            }, {
                "label" : "TERMS",
                "url"   : "https://github.com/cgloeckner/pyvtt/blob/master/TERMS.md"
            }
        ]

        for category in ['discord', 'github']:
            key = f'VTT_LINKS_{category.upper()}'
            value = os.getenv(key)
            if value is not None:
                self.links.append({
                    'label': category.upper(),
                    'url': value
                })
        
        self.notify_api = None # notify api instance
        self.login_api = None   # login api instance
        self.cache = None   # later engine cache

        self.logging = utils.LoggingApi(
            quiet        = self.settings.quiet,
            info_file    = self.paths.get_log_path('info'),
            error_file   = self.paths.get_log_path('error'),
            access_file  = self.paths.get_log_path('access'),
            warning_file = self.paths.get_log_path('warning'),
            logins_file  = self.paths.get_log_path('logins'),
            auth_file    = self.paths.get_log_path('auth'),
            stdout_only  = self.settings.no_logs,
            loglevel     = self.settings.log_level
        )
        
        self.logging.info(f'Started Modes: {sys.argv}')
        self.logging.info(f'Using {self.paths.pref_root} as preference directory')
        
        # load fancy url generator api ... lol
        self.url_generator = utils.FancyUrlApi(self.paths)

        if self.settings.localhost:
            # use localhost as domain
            self.listen = "127.0.0.1"
            self.domain = "localhost"
            self.logging.info("Restricting to localhost")

        else:
            # host publicly
            if self.settings.domain == "":
                # run via public ip
                ip = self.get_public_ip()
                self.domain = ip
                self.logging.info(f"Using Public IP {ip} as Domain")

            self.init_webhooks()
            self.init_oauth()

        self.logging.info('Loading main database...')
        # create main database
        self.orm: dict[str, typing.Any] = {}  # FIXME: delete because of db.entities["Foo"]
        self.main_db = create_main_database(self)
        
        # setup db_session to all routes
        self.app.install(db_session)
        
        # setup error catching
        if self.settings.debug:
            # let bottle catch exceptions
            self.app.catchall = True
        
        else:
            # use custom middleware
            self.error_reporter = utils.ErrorDispatcher(self.get_client_ip, self.logging.error)
            self.app.install(self.error_reporter.plugin)
        
        # dice roll specific timers
        self.recent_rolls = 30 # rolls within past 30s are recent
        self.latest_rolls = 60 * 10 # rolls within the past 10min are up-to-date

        self.git_hash = None
        self.debug_hash = None
        self.load_version_number()

        # export server constants to javascript-file
        self.constants = utils.ConstantExport()
        self.constants.load_from_engine(self)
        self.constants.save_to_file(self.paths.get_constants_path())

        # game cache
        self.cache = EngineCache(self)

    def init_webhooks(self) -> None:
        webhooks = {}
        for api_name in utils.notifier.SUPPORTED_APIS:
            data = utils.parse_webhook_data(api_name, dict(os.environ))
            if data is not None:
                webhooks[api_name] = data

        self.logging.info(f'Found webhook setup for: {[api_name for api_name in webhooks]}')
        
        if len(webhooks) >= 1:
            # FIXME: using the next best webhook API does not allow multiple webhooks
            app_title = f'{self.settings.app_name} on {self.get_domain()}'
            first_hook = webhooks[list(webhooks.keys())[0]]
            self.notify_api = utils.DiscordWebhook(
                app_title=app_title, alias=app_title, url=first_hook['url'], 
                roles=[], users=first_hook['users']
            )

    def init_oauth(self) -> None:
        # collect provider data from environ vars
        providers = {}
        for api_name in utils.auth.SUPPORTED_LOGIN_APIS:
            data = utils.parse_provider_data(api_name, dict(os.environ))
            if data is not None:
                providers[api_name] = data
        
        self.logging.info(f'Found oauth setup for: {
            [api_name for api_name in providers]
        }')
        
        if len(providers) >= 1:
            self.login_api = utils.OAuthClient(
                on_auth=self.logging.auth,
                callback_url=self.get_auth_callback_url(),
                providers=providers
            )

    def load_version_number(self) -> None:
        # load version number
        bn = BuildNumber()
        bn.load_from_file(
            self.paths.get_static_path(default=True) / 'client' / 'version.js'
        )
        self.version = str(bn)
        
        # query latest git hash
        try:
            with open('sha.txt') as h:
                self.git_hash = h.read().split('\n')[0]
        except:
            self.logging.warning('Cannot load git SHA from sha.txt.')
            # fallback
            p = subprocess.run('git rev-parse --short HEAD', shell=True, 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if p.returncode != 0:
                error = p.stderr.decode('utf-8')
                self.logging.error(f'Cannot query git SHa from commandline: {error}')
            else:
                self.git_hash = p.stdout.decode('utf-8').split('\n')[0]

        # generate debug hash
        if self.settings.debug:
            self.debug_hash = uuid.uuid4().hex

    def run(self):
        if self.notify_api is not None:
            self.notify_api.on_start()

        bottle.run(
            host       = self.listen,
            port       = self.settings.port,
            debug      = self.settings.debug,
            quiet      = self.settings.quiet,
            server     = VttServer, # type: ignore
        )
        
    def get_domain(self):
        if self.settings.localhost:
            # because of forced localhost mode
            return 'localhost'
        else:
            # use domain (might be replaced by public ip)
            return self.settings.domain
        
    def get_port(self):
        return self.settings.port
   
    def get_url(self):
        port   = ''
        suffix = ''
        if self.has_ssl():
          suffix = 's'
        else:
          if self.get_port != 80:
            port   = f':{self.get_port()}'
        return f'http{suffix}://{self.get_domain()}{port}'

    def get_websocket_url(self):
        port = ''
        protocol = 'ws'
        if self.has_ssl():
            protocol = 'wss'
        else:
            if self.get_port() != 80:
                port  = f':{self.get_port()}'
        return f'{protocol}://{self.get_domain()}{port}/vtt/websocket'

    def get_auth_callback_url(self):
        port = ''
        protocol = 'http'
        if self.has_ssl():
            protocol = 'https'
        else:
            if self.get_port() != 80:
                port = f':{self.get_port()}'
        return f'{protocol}://{self.get_domain()}{port}/vtt/callback'

    def get_build_sha(self):
        if self.debug_hash is not None:
            return self.debug_hash

        v = self.version
        if self.git_hash is not None:
            v += '-' + self.git_hash
        
        return v

    def has_reverse_proxy(self):
        return self.settings.reverse_proxy

    def has_ssl(self):
        return self.settings.ssl

    def verify_url_section(self, s):
        return bool(re.match(self.url_regex, s))
        
    def get_client_ip(self, request):
        if self.has_reverse_proxy():
            # NOTE: fly.io provides `X-Forwarded-For` with additional information after the comma
            return request.environ.get('HTTP_X_FORWARDED_FOR').split(', ')[0]
        else:
            return request.environ.get('REMOTE_ADDR')

    def get_client_agent(self, request):
        return request.environ.get('HTTP_USER_AGENT')
        
    def get_country_from_ip(self, ip, timeout=3):
        result = '?' # fallback case
        try:
            html = requests.get('http://ip-api.com/json/{0}'.format(ip), timeout=timeout)
            d = json.loads(html.text)
            if 'countryCode' in d:
                result = d['countryCode'].lower()
        except requests.exceptions.ReadTimeout as e:
            self.logging.warning('Cannot query location of IP {0}'.format(ip))
        return result
        
    def get_public_ip(self):
        try:
            return requests.get('https://api.ipify.org').text
        except requests.exceptions.ReadTimeout as e:
            self.logging.warning('Cannot query server\'s ip')
            return 'localhost'

    def parse_login_log(self):

        class LoginRecord(object):
            def __init__(self, timeid, country, ip, agent):
                self.timeid  = timeid
                self.country = country
                self.ip      = ip
                self.agent   = agent
        
        records = list()
        with open(self.paths.get_log_path('logins'), 'r') as h:
            content = h.read()
            for line in content.split('\n'):
                if line == '':
                    continue
                args = json.loads(line)
                records.append(LoginRecord(*args))
        return records

    def on_error(self, error_id: str, message: str) -> None:
        self.logging.error(message)
        if self.notify_api is not None:
            self.notify_api.on_error(error_id, message)

    @staticmethod
    def get_md5(handle):
        hash_md5 = hashlib.md5()
        offset = handle.tell()
        for chunk in iter(lambda: handle.read(4096), b""):
            hash_md5.update(chunk)
        # rewind after reading
        handle.seek(offset)
        return hash_md5.hexdigest()
        
    def get_size(self, file_upload):
        """ Determine size of a file upload.
        """
        offset = file_upload.file.tell()
        size = len(file_upload.file.read())
        file_upload.file.seek(offset)
        return size
        
    def get_supported_dice(self):
        return [2, 4, 6, 8, 10, 12, 20, 100]
        
    def cleanup_all(self):
        """ Deletes all export games' zip files, unused images and
        outdated dice roll results from all games.
        Inactive games or even GMs are deleted
        (see engine.settings.cleanup_expire).
        """
        now = time.time()
        gms   = list()
        games = list()
        num_bytes  = 0
        num_rolls  = 0
        num_tokens = 0
        num_md5s   = 0

        Gm = self.main_db.entities["GM"]

        assert self.cache
        
        with db_session:
            for gm in Gm.select():
                gm_cache = self.cache.get(gm)
                if not gm_cache:
                    continue

                # check if GM expired
                if gm.has_expired(now, gm_cache.db):
                    # remove expired GM
                    num_bytes += gm.pre_delete()
                    gms.append(gm.url)
                    gm.delete()
                    continue

                # cleanup GM's games
                g, b, r, t, m = gm.cleanup(gm_cache.db, now)
                games.extend(g)
                num_bytes  += b
                num_rolls  += r
                num_tokens += t
                num_md5s   += m
        
        # remove all exported games' zip files
        export_path = self.paths.get_export_path()
        num_zips = len(os.listdir(export_path))
        if num_zips > 0:
            num_bytes += os.path.getsize(export_path)
            shutil.rmtree(export_path)
            self.paths.ensure(export_path)

        return gms, games, num_zips, num_bytes, num_rolls, num_tokens, num_md5s

    def save_to_dict(self):
        """ Export all GMs and their games (including scenes and tokens)
        to a single dict. Images and music are NOT included.
        This method's purpose is to allow database schema migration:
        export the database, purge and rebuild, import data.
        """
        gms = list()

        Gm = self.main_db.entities["GM"]

        assert self.cache
        
        # dump GM data (name, session id etc.)
        with db_session:
            for gm in Gm.select():
                gms.append(gm.to_dict())
        
        # dump each GM's games
        for gm in gms:         
            gm_cache = self.cache.get_from_url(gm['url'])
            gm['games'] = dict()
            if not gm_cache:
                continue

            assert gm_cache.db
            Game = gm_cache.db.entities["Game"]
            with db_session:
                for game in Game.select():
                    # fetch all(!) data
                    gm['games'][game.url] = game.to_dict()

        return gms

    def load_from_dict(self, gms):
        """ Import all GMs and their games (including scenes and tokens)
        from a single dict. Images and music are NOT included.
        This method's purpose is to allow database schema migration.
        ONLY CALL THIS WITH EMPTY DATABASES.
        """
        assert self.cache
        
        # create GM data (name, session id etc.)
        with db_session:
            for gm_data in gms:
                self.cache.create_gm(
                    name=gm_data['name'], 
                    identity=gm_data['identity'],
                    metadata=gm_data['metadata'],
                    url=gm_data['url'],
                    sid=gm_data['sid']
                )

        # create Games
        for gm_data in gms:
            gm_cache = self.cache.get_from_url(gm_data['url'])
            if not gm_cache:
                continue
        
            gm_cache.connect_db()
            assert gm_cache.db
            with db_session:
                for url in gm_data['games']:
                    game = gm_cache.create_game(url=url)
                    gm_cache.db.commit()
                    game.from_dict(gm_data['games'][url])
                    gm_cache.db.commit()
