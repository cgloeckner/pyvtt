#!/usr/bin/python3
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import os, sys, hashlib, time, requests, json, re, shutil, pathlib

import bottle

from orm import db_session, createMainDatabase
from server import VttServer
from cache import EngineCache

from buildnumber import BuildNumber

import utils 


__author__ = 'Christian Glöckner'
__licence__ = 'MIT'



class Engine(object):

    def __init__(self, argv=list(), pref_dir=None):
        appname = 'pyvtt'
        for arg in argv:
            if arg.startswith('--appname='):
                appname = arg.split('--appname=')[1]

            elif arg.startswith('--prefdir='):
                pref_dir = arg.split('--prefdir=')[1]
        
        self.paths     = utils.PathApi(appname=appname, root=pref_dir)
        
        # setup per-game stuff
        self.checksums = dict()
        self.locks     = dict()
        
        # webserver stuff
        self.listen = '0.0.0.0'
        self.hosting = {
            'domain'      : 'localhost',
            'port'        : 8080,
            'socket'      : '',
            'ssl'         : False,
            'reverse'     : False
        }
        self.debug  = False
        self.quiet  = False
        self.shards = list()
        
        self.main_db = None
        
        # blacklist for GM names and game URLs
        self.gm_blacklist = ['', 'static', 'token', 'music', 'vtt', 'websocket', 'thumbnail']
        self.url_regex    = '^[A-Za-z0-9_\-.]+$'
        
        # maximum file sizes for uploads (in MB)
        self.file_limit = {
            "token"      : 2,
            "background" : 10,
            "game"       : 30,
            "music"      : 10,
            "num_music"  : 5
        }
        self.playercolors = ['#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF']
        
        self.local_gm       = False
        self.localhost      = False
        self.title          = appname
        self.links          = list()
        self.expire         = 3600 * 24 * 30 # default: 30d
        self.login          = dict() # login settings
        self.login['type']  = ''
        self.login_api      = None   # login api instance
        self.notify         = dict() # crash notify settings
        self.notify['type'] = ''
        self.notify_api     = None   # notify api instance
        
        self.cache         = None   # later engine cache

        # handle commandline arguments
        self.debug     = '--debug' in argv
        self.quiet     = '--quiet' in argv
        self.local_gm  = '--local-gm' in argv
        self.localhost = '--localhost' in argv
        
        if self.localhost:
            assert(not self.local_gm)

        self.logging = utils.LoggingApi(
            quiet        = self.quiet,
            info_file    = self.paths.getLogPath('info'),
            error_file   = self.paths.getLogPath('error'),
            access_file  = self.paths.getLogPath('access'),
            warning_file = self.paths.getLogPath('warning'),
            stats_file   = self.paths.getLogPath('stats'),
            auth_file    = self.paths.getLogPath('auth')
        )
        
        self.logging.info('Started Modes: debug={0}, quiet={1}, local_gm={2} localhost={3}'.format(self.debug, self.quiet, self.local_gm, self.localhost))
        
        # load fancy url generator api ... lol
        self.url_generator = utils.FancyUrlApi(self.paths)

        # handle settings
        settings_path = self.paths.getSettingsPath()
        if not os.path.exists(settings_path):
            # create default settings
            settings = {
                'title'        : self.title,
                'links'        : self.links,
                'file_limit'   : self.file_limit,
                'playercolors' : self.playercolors,
                'shards'       : self.shards,
                'expire'       : self.expire,
                'hosting'      : self.hosting,
                'login'        : self.login,
                'notify'       : self.notify
            }
            with open(settings_path, 'w') as h:
                json.dump(settings, h, indent=4)
                self.logging.info('Created default settings file')
        else:
            # load settings
            with open(settings_path, 'r') as h:
                settings = json.load(h)
                self.title        = settings['title']
                self.links        = settings['links']
                self.file_limit   = settings['file_limit']
                self.playercolors = settings['playercolors']
                self.shards       = settings['shards']
                self.expire       = settings['expire']
                self.hosting      = settings['hosting']
                self.login        = settings['login']
                self.notify       = settings['notify']
            self.logging.info('Settings loaded')

        # add this server to the shards list
        self.shards.append(self.getUrl())
        
        # export server constants to javascript-file
        self.constants = utils.ConstantExport()
        self.constants(self)
        
        # show argv help
        if '--help' in argv:
            print('Commandline args:')
            print('    --debug       Starts in debug mode.')
            print('    --quiet       Starts in quiet mode.')
            print('    --local-gm    Starts in local-GM-mode.')
            print('    --localhost   Starts in localhost mode.')
            print('')
            print('Debug Mode:     Enables debug level logging.')
            print('Quiet Mode:     Disables verbose outputs.')
            print('Local-GM Mode:  Replaces `localhost` in all created links by the public ip.')
            print('Localhost Mode: Restricts server for being used via localhost only. CANNOT BE USED WITH --local-gm')
            print('')
            print('See {0} for custom settings.'.format(settings_path))
            sys.exit(0)

        self.logging.info('Loading domain...')
        if self.localhost:
            # run via localhost
            self.listen = '127.0.0.1'
            self.hosting['domain'] = 'localhost'
            self.logging.info('Overwriting connections to localhost')
        elif self.local_gm or self.hosting['domain'] == '':
            # run via public ip
            self.hosting['domain'] = self.getPublicIp()
            self.logging.info('Overwriting Domain by Public IP: {0}'.format(self.hosting['domain']))

        
        self.logging.info('Loading login API...')
        if self.local_gm:
            self.login['type'] = ''
            self.logging.info('Defaulting to dev-login for local-gm')
        else:
            # load patreon API
            if self.login['type'] in ['patreon', 'google']:
                if self.login['type'] == 'patreon':
                    # create patreon query API
                    self.login_api = utils.PatreonApi(engine=self, **self.login)
                elif self.login['type'] == 'google':
                    # create google query API
                    self.login_api = utils.GoogleApi(engine=self, **self.login)
                else:
                    raise NotImplementedError(self.login['type'])
            
        if self.notify['type'] == 'email':
            # create email notify API
            self.notify_api = utils.EmailApi(self, appname=appname, **self.notify)

        self.logging.info('Loading main database...')
        # create main database
        self.main_db = createMainDatabase(self)
        
        # setup db_session to all routes
        self.app = bottle.default_app()
        self.app.install(db_session)
        
        # setup error catching
        if self.debug:
            # let bottle catch exceptions
            self.app.catchall = True
        
        else:
            # use custom middleware
            self.error_reporter = utils.ErrorReporter(self)
            self.app.install(self.error_reporter.plugin)
        
        # dice roll specific timers
        self.recent_rolls = 30 # rolls within past 30s are recent
        self.latest_rolls = 60 * 10 # rolls within the past 10min are up-to-date

        # load version number
        bn = BuildNumber()
        bn.loadFromFile(pathlib.Path('static') / 'version.js')
        self.version = str(bn)
        
        
        # game cache
        self.cache = EngineCache(self)
        
    def run(self):
        certfile = ''
        keyfile  = ''
        if self.hasSsl():
            # enable SSL
            ssl_dir = self.paths.getSslPath()
            certfile = ssl_dir / 'cacert.pem'
            keyfile  = ssl_dir / 'privkey.pem'
            assert(os.path.exists(certfile))
            assert(os.path.exists(keyfile))
        
        ssl_args = {'certfile': certfile, 'keyfile': keyfile} if self.hasSsl() else {}
        
        if self.notify_api is not None:
            self.notify_api.notifyStart()
        
        bottle.run(
            host       = self.listen,
            port       = self.hosting['port'],
            debug      = self.debug,
            quiet      = self.quiet,
            server     = VttServer,
            # VttServer-specific
            unixsocket = self.hosting['socket'],
            # SSL-specific
            **ssl_args
        )
        
    def getDomain(self):
        if self.localhost:
            # because of forced localhost mode
            return 'localhost'
        else:
            # use domain (might be replaced by public ip)
            return self.hosting['domain']
        
    def getPort(self):
        return self.hosting['port']
        
    def getUrl(self):
        suffix = 's' if self.hasSsl() else ''
        return f'http{suffix}://{self.getDomain()}:{self.getPort()}'

    def getWebsocketUrl(self):
        suffix = 's' if self.hasSsl() else ''
        return f'ws{suffix}://{self.getDomain()}:{self.getPort()}/websocket'

    def getAuthCallbackUrl(self):
        return f'https://{self.getDomain()}/vtt/callback'

    def hasSsl(self):
        return self.hosting['ssl']
        
    def verifyUrlSection(self, s):
        return bool(re.match(self.url_regex, s))
        
    def getClientIp(self, request):
        # use different header if through unix socket or reverse proxy
        if self.hosting['socket'] != '' or self.hosting['reverse']:
            return request.environ.get('HTTP_X_FORWARDED_FOR')
        else:
            return request.environ.get('REMOTE_ADDR')

    def getClientAgent(self, request):
        return request.environ.get('HTTP_USER_AGENT')
        
    def getCountryFromIp(self, ip, timeout=3):
        result = '?' # fallback case
        try:
            html = requests.get('http://ip-api.com/json/{0}'.format(ip), timeout=timeout)
            d = json.loads(html.text)
            if 'countryCode' in d:
                result = d['countryCode'].lower()
        except requests.exceptions.ReadTimeout as e:
            self.logging.warning('Cannot query location of IP {0}'.format(ip))
        return result
        
    def getPublicIp(self):
        try:
            return requests.get('https://api.ipify.org').text
        except requests.exceptions.ReadTimeout as e:
            self.logging.warning('Cannot query server\'s ip')
            return 'localhost'
        
    @staticmethod
    def getMd5(handle):
        hash_md5 = hashlib.md5()
        offset = handle.tell()
        for chunk in iter(lambda: handle.read(4096), b""):
            hash_md5.update(chunk)
        # rewind after reading
        handle.seek(offset)
        return hash_md5.hexdigest()
        
    def getSize(self, file_upload):
        """ Determine size of a file upload.
        """
        offset = file_upload.file.tell()
        size = len(file_upload.file.read())
        file_upload.file.seek(offset)
        return size
        
    def getSupportedDice(self):
        return [2, 4, 6, 8, 10, 12, 20, 100]
        
    def cleanup(self):
        """ Deletes all export games' zip files, unused images and
        outdated dice roll results from all games.
        Inactive games or even GMs are deleted (see engine.expired).
        """
        now = time.time()
        
        with db_session:
            for gm in self.main_db.GM.select():
                gm_cache = self.cache.get(gm)
                
                # check if GM expired
                if gm.hasExpired(now):
                    # remove expired GM
                    gm.preDelete()
                    gm.delete() 
                    
                else:
                    # cleanup GM's games
                    gm.cleanup(gm_cache.db, now)
        
        # remove all exported games' zip files 
        export_path = self.paths.getExportPath()
        num_files = len(os.listdir(export_path))
        if num_files > 0:
            shutil.rmtree(export_path)
            self.paths.ensure(export_path)
            self.logging.info('Removed {0} game ZIPs'.format(num_files))

    def saveToDict(self):
        """ Export all GMs and their games (including scenes and tokens)
        to a single dict. Images and music are NOT included.
        This method's purpose is to allow database schema migration:
        export the database, purge and rebuild, import data.
        """
        gms = list()

        # dump GM data (name, session id etc.)
        with db_session:
            for gm in self.main_db.GM.select():
                gms.append(gm.to_dict())
        
        # dump each GM's games
        for gm in gms:         
            gm_cache = self.cache.getFromUrl(gm['url'])
            gm['games'] = dict()
            with db_session:
                for game in gm_cache.db.Game.select():
                    # fetch all(!) data
                    gm['games'][game.url] = game.toDict()

        return gms

    def loadFromDict(self, gms):
        """ Import all GMs and their games (including scenes and tokens)
        from a single dict. Images and music are NOT included.
        This method's purpose is to allow database schema migration.
        ONLY CALL THIS WITH EMPTY DATABASES.
        """
        # create GM data (name, session id etc.)
        with db_session:
            for gm_data in gms:
                gm = self.main_db.GM(name=gm_data['name'], url=gm_data['url'],
                                     sid=gm_data['sid'])
                gm.postSetup() # NOTE: timeid is overwritten here
                self.cache.insert(gm)

        # create Games
        for gm_data in gms:
            gm_cache = self.cache.getFromUrl(gm_data['url'])
            gm_cache.connect_db()
            with db_session:
                for url in gm_data['games']:
                    game = gm_cache.db.Game(url=url, gm_url=gm_data['url'])
                    game.postSetup()
                    gm_cache.db.commit()
                    game.fromDict(gm_data['games'][url])
                    gm_cache.db.commit()
                    
