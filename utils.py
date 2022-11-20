#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import sys, os, logging, smtplib, pathlib, tempfile, traceback, uuid, random, base64, json

import bottle       

from gevent import lock

from authlib.integrations.requests_client import OAuth2Session
from authlib.oidc.core import CodeIDToken
from authlib.jose import jwt


__author__ = 'Christian Glöckner'
__licence__ = 'MIT'



class BuildNumber(object):

    def __init__(self):
        self.version = [0, 0, 1]

    def __str__(self):
        return '{0}.{1}.{2}'.format(*self.version)

    def loadFromFile(self, fname):
        """ Load version number from single-line javascript file. """
        with open(fname, 'r') as h:
            line = h.read()
        version = line.split('"')[1].split('.')
        for i in [0, 1, 2]:
            version[i] = int(version[i])

        self.version = version

    def saveToFile(self, fname):
        """ Rewrite javascript file for new version number. """
        raw = 'const version = "{0}";'.format(self)
        with open(fname, 'w') as h:
            h.write(raw)

    def inc(self, k):
        self.version[k] += 1
        for i in range(k+1, len(self.version)):
            self.version[i] = 0

    def major(self):
        self.inc(0)

    def minor(self):
        self.inc(1)

    def fix(self):
        self.inc(2)


# ---------------------------------------------------------------------

def addDictSet(dictionary, key, value):
    """ Add the value to a set inside the dictionary, specified by the
    key. If the set does not exist yet, it will be added.
    """
    if key not in dictionary:
        dictionary[key] = set()
    dictionary[key].add(value)


def countDictSetLen(dictionary):
    """ Override each set in the dict with its length.
    """
    for key in dictionary:
        dictionary[key] = len(dictionary[key])


# ---------------------------------------------------------------------

# API for providing local harddrive paths
class PathApi(object):
    
    def __init__(self, appname, root=None):
        """ Uses given root or pick standard preference directory. """
        if root is None:
            # get preference dir
            p = pathlib.Path.home()
            if sys.platform.startswith('linux'):
                p = p / ".local" / "share"
            else:
                raise NotImplementedError('only linux supported yet')
            
            self.root = p / appname
        else:
            self.root = pathlib.Path(root) / appname
        
        # make sure paths exists
        self.ensure(self.root)
        self.ensure(self.getExportPath())
        self.ensure(self.getGmsPath())
        self.ensure(self.getFancyUrlPath())
        self.ensure(self.getStaticPath())
        self.ensure(self.getAssetsPath())
        self.ensure(self.getClientCodePath())
        
    def ensure(self, path):
        if not os.path.isdir(path):
            os.mkdir(path)
        
    # Engine paths
        
    def getStaticPath(self):
        return self.root / 'static'
    
    def getAssetsPath(self):
        return self.getStaticPath() / 'assets'

    def getClientCodePath(self):
        return self.getStaticPath() / 'client'
 
    def getLogPath(self, fname):
        return self.root / '{0}.log'.format(fname)
        
    def getSettingsPath(self):
        return self.root / 'settings.json'
        
    def getMainDatabasePath(self):
        return self.root / 'main.db'

    def getConstantsPath(self):
        return self.getClientCodePath() / 'constants.js'
 
    def getSslPath(self):
        return self.root / 'ssl'
           
    def getExportPath(self):
        return self.root / 'export'
        
    def getGmsPath(self, gm=None):
        p = self.root / 'gms'
        if gm is not None:
            p /= gm
        return p
        
    def getFancyUrlPath(self, fname=None):
        p = self.root / 'fancyurl'
        if fname is not None:
            p /= '{0}.txt'.format(fname)
        return p
        
    # GM- and Game-relevant paths
        
    def getDatabasePath(self, gm):
        return self.getGmsPath(gm) / 'gm.db'
        
    def getGamePath(self, gm, game):
        return self.getGmsPath(gm) / game 

    def getMd5Path(self, gm, game):
        return self.getGamePath(gm, game) / 'gm.md5'


# ---------------------------------------------------------------------

# Email API for error notification
# @NOTE: this class is not covered in the unit tests because it depends too much on external resources
class EmailApi(object):
    
    def __init__(self, engine, **data):
        self.engine   = engine
        self.appname  = data['appname']
        self.host     = data['host']
        self.port     = data['port']
        self.sender   = data['sender']
        self.user     = data['user']
        self.password = data['password']
        self.lock = lock.RLock()
        self.login()
        
    def login(self):
        with self.lock:
            self.smtp = smtplib.SMTP(f'{self.host}:{self.port}')
            self.smtp.starttls()
            self.smtp.login(self.user, self.password)

    def send(self, subject, message):
        # create mail content
        frm = f'From: pyvtt Server <{self.sender}>'
        to  = f'To: Developers <{self.sender}>'
        sub = f'Subject: [{self.appname}/{self.engine.title}] {subject}'
        plain = f'{frm}\n{to}\n{sub}\n{message}'
        
        # send email
        try:
            with self.lock:
                self.smtp.sendmail(self.sender, self.sender, plain)
        except smtplib.SMTPSenderRefused:
            # re-login and re-try
            self.login()
            self.smtp.sendmail(self.sender, self.sender, plain)
        
    def onStart(self):
        msg = f'The VTT server {self.appname}/{self.engine.title} on {self.engine.getDomain()} is now online!'
        self.send('Server Online', msg)

    def onCleanup(self, report):
        report = json.dumps(report, indent=4)
        msg = f'The VTT Server finished cleanup.\n{report}'
        self.send('Periodic Cleanup', msg)

    def onError(self, error_id, message):
        sub = f'Exception Traceback #{error_id}'
        self.send(sub, message)


# ---------------------------------------------------------------------

# @NOTE: this class is not covered in the unit tests because it depends too much on external resources
class BaseLoginApi(object):

    def __init__(self, api, engine, **data):
        self.api           = api
        self.engine        = engine
        self.callback      = engine.getAuthCallbackUrl() # https://example.com/my/callback/path
        self.client_id     = data['client_id']     # ID of API key
        self.client_secret = data['client_secret'] # Secret of API key

        self.login_caption = f'Login with {api}'
        
        # thread-safe structure to hold login sessions
        self.sessions = dict()
        self.lock     = lock.RLock()

    def getLogoutUrl(self):
        raise NotImplementedError()

    def getGmInfo(self, url):
        return ''
    
    def loadSession(self, state):
        """Query session via state but remove it from the cache"""
        with self.lock:
            return self.sessions.pop(state)

    def saveSession(self, state, session):
        with self.lock:
            self.sessions[state] = session

    @staticmethod
    def parseStateFromUrl(url):
        # query state from url (which contains '&state=foo')
        return url.split('&state=')[1].split('&')[0]

    def getIconUrl(self, key):
        return self.engine.login['icons'][key]


# ---------------------------------------------------------------------

# @NOTE: this class is not covered in the unit tests because it depends too much on external resources
class Auth0Api(BaseLoginApi):

    def __init__(self, engine, **data):
        super().__init__('auth0', engine, **data)
        self.login_caption   = 'Click to Login'
        self.auth_endpoint   = f'https://{data["domain"]}/authorize'
        self.logout_endpoint = f'https://{data["domain"]}/v2/logout'
        self.token_endpoint  = f'https://{data["domain"]}/oauth/token'

        self.logout_callback = engine.getUrl()
        
        #if engine.debug:
        #    # accept non-https for testing oauth (e.g. localhost)
        #    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    def getAuthUrl(self):
        """ Generate external oauth URL to access in order to fetch data. """
        # create session, redirect uri and state
        s = OAuth2Session(
            client_id=self.client_id,
            client_secret=self.client_secret,
            scope='openid profile email',
            redirect_uri=self.callback
        )
        uri, state = s.create_authorization_url(self.auth_endpoint)
        self.saveSession(state, s)
        
        return uri
    
    def getLogoutUrl(self):
        return f'{self.logout_endpoint}?client_id={self.client_id}&returnTo={self.logout_callback}'

    def getSession(self, request):
        """ Query google to return required user data and infos."""
        state = BaseLoginApi.parseStateFromUrl(request.url)

        # fetch token
        try:
            s = self.loadSession(state)
        except KeyError:
            return {}
        
        token = s.fetch_token(
            url=self.token_endpoint,
            authorization_response=request.url
        )

        # fetch payload from base64 ID-Token
        id_token = token['id_token']
        self.engine.logging.info(f'GM Login with {id_token}')
        header, payload, signature = id_token.split('.')

        payload += '=' * (4-len(payload) % 4)
        data = base64.b64decode(payload)
        data = json.loads(data)
        
        # create login data
        result = {
            'name'     : data['name'],
            'identity' : data['email'],
            'metadata' : data['sub']
        }
        if 'auth0' in data['sub']:
            # split name from email login
            result['name'] = data['name'].split('@')[0]
        
        self.engine.logging.auth(result)
        
        return result

    @staticmethod
    def parseProvider(s):
        provider = '-'.join(s.split('|')[:-1])
        
        # split 'oauth2'-section from provider
        for s in ['-oauth2', 'oauth2-']:
            provider = provider.replace(s, '')

        return provider.lower()


# ---------------------------------------------------------------------

class LoggingApi(object):

    def __init__(self, quiet, info_file, error_file, access_file, warning_file, logins_file, auth_file, stdout_only=False, loglevel='INFO'):
        self.log_format = logging.Formatter('[%(asctime)s at %(module)s/%(filename)s:%(lineno)d] %(message)s')
        
        # setup info logger
        self.info_logger = logging.getLogger('info_log')
        self.info_logger.setLevel(loglevel)
        
        if not stdout_only:
            self.linkFile(self.info_logger, info_file)
        if not quiet:
            self.linkStdout(self.info_logger)
        
        # setup error logger
        self.error_logger = logging.getLogger('error_log')   
        self.error_logger.setLevel(loglevel)
        
        if not stdout_only:
            self.linkFile(self.error_logger, error_file)
        elif not quiet:
            self.linkStdout(self.error_logger)
        
        # setup access logger
        self.access_logger = logging.getLogger('access_log')
        self.access_logger.setLevel(loglevel)

        if not stdout_only:
            self.linkFile(self.access_logger, access_file)
        if not quiet:
            self.linkStdout(self.access_logger)
        
        # setup warning logger
        self.warning_logger = logging.getLogger('warning_log')   
        self.warning_logger.setLevel(loglevel)
        
        if not stdout_only:
            self.linkFile(self.warning_logger, warning_file)
        if not quiet:
            self.linkStdout(self.warning_logger)
        
        # setup logins logger
        self.logins_logger = logging.getLogger('logins_log')   
        self.logins_logger.setLevel(loglevel)
        
        # @NOTE: this log is required for server analysis and cannot be disabled
        self.linkFile(self.logins_logger, logins_file, skip_format=True)
        
        # setup auth logger
        self.auth_logger = logging.getLogger('auth_log')
        self.auth_logger.setLevel(logging.INFO)
        
        if not stdout_only:
            self.linkFile(self.auth_logger, auth_file)
        if not quiet:
            self.linkStdout(self.auth_logger)
        
        # link logging handles
        self.info    = self.info_logger.info
        self.error   = self.error_logger.error
        self.access  = self.access_logger.info
        self.warning = self.warning_logger.warning
        self.logins  = self.logins_logger.info
        self.auth    = self.auth_logger.info

        if not stdout_only:
            boot = '{0} {1} {0}'.format('=' * 15, 'STARTED')
            self.info(boot)
            self.error(boot)
            self.access(boot)
            self.warning(boot)
    
    def linkStdout(self, target):
        """Links the given logger to stdout."""
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(self.log_format)
        target.addHandler(handler)

    def linkFile(self, target, fname, skip_format=False):
        """Links the given logger to the provided filename."""
        handler = logging.FileHandler(fname, mode='a')
        if not skip_format:
            handler.setFormatter(self.log_format)
        target.addHandler(handler)
    

# ---------------------------------------------------------------------

# @NOTE: this class is not covered in the unit tests but during integration test
class ErrorReporter(object):

    def __init__(self, engine):
        self.engine = engine
        
    def getStacktrace(self):
        # fetch exception traceback
        with tempfile.TemporaryFile(mode='w+') as h:
            traceback.print_exc(file=h)
            h.seek(0) # rewind after writing
            return h.read()
        
    def plugin(self, func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except bottle.HTTPResponse as e:
                raise
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception as error:
                # fetch stacktrace and other debugging data
                stacktrace = self.getStacktrace()
                error_id   = uuid.uuid1().hex
                full_url   = bottle.request.fullpath
                client_ip  = self.engine.getClientIp(bottle.request)
                # dump cookies
                cookies    = ''
                for key in bottle.request.cookies.keys():
                    cookies += '\t{0} : {1}\n'.format(key, bottle.request.cookies[key])
                if cookies == '':
                    cookies = '{}'
                else:
                    cookies = '{\n' + cookies + '}'
                # dump metadata (e.g. in case of websocket error)
                meta_dump = ''
                try:
                    data = error.metadata
                    for key in data:
                        meta_dump += '\t{0} : {1}\n'.format(key, data[key])
                    if meta_dump == '':
                        meta_dump = '{}'
                    else:
                        meta_dump = '{\n' + meta_dump + '}'
                except AttributeError:
                    meta_dump = '{}'
                message = 'Error ID  = #{0}\nRoute URL = {1}\nClient-IP = {2}\nCookies   = {3}\nMetadata   = {4}\n\n{5}'.format(
                    error_id, full_url, client_ip, cookies, meta_dump, stacktrace)
                
                # log error and notify developer
                self.engine.logging.error(message)
                if self.engine.notify_api is not None:
                    self.engine.notify_api.onError(error_id, message)
                
                # notify user about error
                if bottle.request.is_ajax:
                    # cause handling in javascript
                    bottle.abort(500, error_id)
                else:
                    # custom errorpage
                    bottle.redirect('/vtt/error/{0}'.format(error_id))
        return wrapper


# ---------------------------------------------------------------------

class FancyUrlApi(object):
    
    def __init__(self, paths):
        self.paths = paths
        self.parts = dict()
        
        # create default words if necessary
        v = ['be', 'have', 'do', 'say', 'go', 'get', 'make', 'know', 'think', 'take']
        a = ['able', 'bad', 'best', 'better', 'big', 'black', 'certain', 'clear', 'different', 'early', 'easy']
        n = ['area', 'book', 'business', 'case', 'child', 'company', 'country', 'day', 'eye', 'fact']
        for t in [('verbs', v), ('adjectives', a), ('nouns', n)]:
            p = self.paths.getFancyUrlPath(t[0])
            if not os.path.exists(p):
                with open(p, mode='w') as h:
                    h.write('\n'.join(t[1]))
        
        # load word lists
        for p in ['verbs', 'adjectives', 'nouns']:
            self.parts[p] = self.load(p)
        
    def load(self, fname):
        # load words
        p = self.paths.getFancyUrlPath(fname)
        with open(p, mode='r') as h:
            content = h.read()
        words = content.split('\n')
        if words[-1] == '':
            # ignore empty line at eof
            words.pop()
        
        # test words not being empty
        for w in words:
            assert(w != '')
            
        return words
        
    @staticmethod
    def pick(src):
        index = random.randrange(0, len(src) - 1)
        return src[index]
        
    def __call__(self):
        """ Generate a random url using <verb>-<adverb>-<noun>.
        """
        results = []
        for p in self.parts:
            l = self.parts[p]
            w = FancyUrlApi.pick(l)
            results.append(w)
        return '-'.join(results)

   
# ---------------------------------------------------------------------

# Exports Constants to a JavaScript-File to allow their use client-side, too
class ConstantExport(object):
    
    def __init__(self):
        self.data = dict()

    def __setitem__(self, key, value):
        """ @NOTE: key will be the javascript-identifier. But there
        is no syntax test here, this is up to the caller.
        """
        self.data[key] = value

    def saveToMemory(self):
        out = '';
        for key in self.data:
            raw = self.data[key]
            if isinstance(raw, str):
                raw = '"{0}"'.format(raw)
            elif raw == True:
                raw = 'true'
            elif raw == False:
                raw = 'false'
            out += 'var {0} = {1};\n'.format(key, raw)
        return out

    def saveToFile(self, fname):
        content = '/** DO NOT MODIFY THIS FILE. IT WAS CREATED AUTOMATICALLY. */\n'
        content += self.saveToMemory()
        with open(fname, 'w') as h:
            h.write(content)

    def __call__(self, engine):
        import orm
        self['MAX_SCENE_WIDTH']  = orm.MAX_SCENE_WIDTH
        self['MAX_SCENE_HEIGHT'] = orm.MAX_SCENE_HEIGHT
        self['MIN_TOKEN_SIZE']   = orm.MIN_TOKEN_SIZE
        self['MAX_TOKEN_SIZE']   = orm.MAX_TOKEN_SIZE
        
        self['MAX_TOKEN_FILESIZE']      = engine.file_limit['token']
        self['MAX_BACKGROUND_FILESIZE'] = engine.file_limit['background']
        self['MAX_GAME_FILESIZE']       = engine.file_limit['game']
        self['MAX_MUSIC_FILESIZE']      = engine.file_limit['music']
        self['MAX_MUSIC_SLOTS']         = engine.file_limit['num_music']

        self['SUGGESTED_PLAYER_COLORS'] = engine.playercolors
        
        self.saveToFile(engine.paths.getConstantsPath())

