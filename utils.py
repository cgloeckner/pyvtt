#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import sys, os, logging, smtplib, pathlib, tempfile, traceback, uuid, random, base64, json

import bottle
import patreon

from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
import google.auth.transport.requests

from authlib.integrations.requests_client import OAuth2Session
from authlib.oidc.core import CodeIDToken
from authlib.jose import jwt


__author__ = 'Christian Glöckner'
__licence__ = 'MIT'



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
        
    def ensure(self, path):
        if not os.path.isdir(path):
            os.mkdir(path)
        
    # Engine paths
        
    def getStaticPath(self):
        return self.root / 'static'
        
    def getLogPath(self, fname):
        return self.root / '{0}.log'.format(fname)
        
    def getSettingsPath(self):
        return self.root / 'settings.json'
        
    def getMainDatabasePath(self):
        return self.root / 'main.db'

    def getConstantsPath(self):
        return self.getStaticPath() / 'constants.js'
 
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
        self.login()
        
    def login(self):
        self.smtp = smtplib.SMTP('{0}:{1}'.format(self.host, self.port))
        self.smtp.starttls()
        self.smtp.login(self.user, self.password)
        
    def notifyStart(self):
        # create mail content
        frm = 'From: pyvtt Server <{0}>'.format(self.sender)
        to  = 'To: Developers <{0}>'.format(self.sender)
        sub = 'Subject: [{0}/{1}] Server Online'.format(self.appname, self.engine.title)
        plain = '{0}\n{1}\n{2}\nThe VTT server {3}/{4} on {5} is now online!'.format(frm, to, sub, self.appname, self.engine.title, self.engine.getDomain())
        
        # send email
        try:
            self.smtp.sendmail(self.sender, self.sender, plain)
        except smtplib.SMTPSenderRefused:
            # re-login and re-try
            self.login()
            self.smtp.sendmail(self.sender, self.sender, plain)
        
    def __call__(self, error_id, message):
        # create mail content
        frm = 'From: pyvtt Server <{0}>'.format(self.sender)
        to  = 'To: Developers <{0}>'.format(self.sender)
        sub = 'Subject: [{1}/{2}] Exception Traceback #{0}'.format(error_id, self.appname, self.engine.title)
        plain = '{0}\n{1}\n{2}\n{3}'.format(frm, to, sub, message)
        
        # send email
        try:
            self.smtp.sendmail(self.sender, self.sender, plain)
        except smtplib.SMTPSenderRefused:
            # re-login and re-try
            self.login()
            self.smtp.sendmail(self.sender, self.sender, plain)


# ---------------------------------------------------------------------

# @NOTE: this class is not covered in the unit tests because it depends too much on external resources
class BaseLoginApi(object):

    def __init__(self, api, engine, **data):
        self.api           = api
        self.engine        = engine
        self.callback      = engine.getAuthCallbackUrl() # https://example.com/my/callback/path
        self.client_id     = data['client_id']     # ID of API key
        self.client_secret = data['client_secret'] # Secret of API key


# ---------------------------------------------------------------------


# @NOTE: this class is not covered in the unit tests because it depends too much on external resources
class GoogleApi(BaseLoginApi):

    def __init__(self, engine, **data):
        super().__init__('google', engine, **data)

        if engine.debug:
            # accept non-https for testing oauth (e.g. localhost)
            os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        self.flow = Flow.from_client_config(
            client_config={
                'web': {
                    'client_id'    : self.client_id,
                    'client_secret': self.client_secret,
                    'auth_uri'     : 'https://accounts.google.com/o/oauth2/auth',
                    'token_uri'    : 'https://oauth2.googleapis.com/token'
                }
            },
            scopes=[
                'https://www.googleapis.com/auth/userinfo.profile',
                'openid'
            ],
            redirect_uri=self.callback)

    def getAuthUrl(self):
        """ Generate google-URL to access in order to fetch data. """
        auth_url, state = self.flow.authorization_url()
        return auth_url
    
    def getSession(self, request):
        """ Query google to return required user data and infos."""
        self.flow.fetch_token(authorization_response=bottle.request.url)
        creds = self.flow.credentials
        token_request = google.auth.transport.requests.Request()

        id_info = id_token.verify_oauth2_token(
            id_token=creds._id_token,
            request=token_request,
            audience=self.client_id
        )

        result = {
            'sid'  : str(uuid.uuid4()),
            'user' : {
                'id'      : id_info.get('sub'),
                'username': id_info.get('name')
            },
            'granted': True # no reason for something else here
        }
        self.engine.logging.auth(result)
        
        return result

# ---------------------------------------------------------------------

# @NOTE: this class is not covered in the unit tests because it depends too much on external resources
class Auth0Api(BaseLoginApi):

    def __init__(self, engine, **data):
        super().__init__('auth0', engine, **data)
        self.auth_endpoint  = f'https://{data["domain"]}/authorize'
        self.token_endpoint = f'https://{data["domain"]}/oauth/token'

        if engine.debug:
            # accept non-https for testing oauth (e.g. localhost)
            os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        self.session = OAuth2Session(
            client_id=self.client_id,
            client_secret=self.client_secret,
            scope='openid profile',
            redirect_uri=self.callback
        )

    def getAuthUrl(self):
        """ Generate external oauth URL to access in order to fetch data. """
        uri, state = self.session.create_authorization_url(self.auth_endpoint)
        return uri
    
    def getSession(self, request):
        """ Query google to return required user data and infos."""
        token = self.session.fetch_token(
            url=self.token_endpoint,
            authorization_response=request.url
        )

        # fetch header from base64 ID-Token
        raw = token['id_token']
        l = len(raw) % 4
        raw += '=' * l
        raw = base64.b64decode(raw)
        
        data = raw.split(b'}')[1] + b'}'
        data = json.loads(data)

        # create base64 userid from subscription
        userid = base64.urlsafe_b64encode(data['sub'].encode('utf-8')).decode('utf-8')

        # create login data
        result = {
            'sid'  : str(uuid.uuid4()),
            'provider': data['sub'].split('|')[0],
            'user' : {
                'id'      : userid,
                'username': data['name']
            },
            'granted': True # no reason for something else here
        }
        self.engine.logging.auth(result)
        
        return result

# ---------------------------------------------------------------------

# @NOTE: this class is not covered in the unit tests because it depends too much on external resources
class PatreonApi(BaseLoginApi):
    
    def __init__(self, engine, **data):
        super().__init__('patreon', engine, **data)

        self.min_pledge    = data['min_pledge']    # minimum pledge level for access (amount)
        self.whitelist     = data['whitelist']     # whitelist to ignore pledge level
    
    @staticmethod
    def getUserInfo(json_data):
        return {
            'id'       : int(json_data['data']['id']),
            'username' : json_data['data']['attributes']['full_name']
        }
        
    @staticmethod
    def getPledgeTitles(json_data):
        titles = dict()
        
        if 'included' not in json_data:
            return titles
        
        for item in json_data['included']:
            attribs = item['attributes']
            if 'title' in attribs and 'amount_cents' in attribs:
                title  = attribs['title']
                amount = attribs['amount_cents']
                titles[amount] = title
        
        return titles
        
    @staticmethod
    def getUserPledgeAmount(json_data):
        amount = 0
        for r in json_data['data']['relationships']['pledges']['data']:
            if r['type'] == 'pledge':
                # search included stuff for pledge_id
                for item in json_data['included']:
                    if item['id'] == r['id']:
                        cents = item['attributes']['amount_cents']
                        if cents > amount:
                            amount = cents
        return amount
        
    def getAuthUrl(self):
        """ Generate patreon-URL to access in order to fetch data. """
        return 'https://www.patreon.com/oauth2/authorize?response_type=code&client_id={0}&redirect_uri={1}'.format(self.client_id, self.callback)
        
    def getApiClient(self, request):
        """ Called after callback was triggered to fetch acccess_token and
        API instance.
        Returns (token, api)
        """
        oauth_client = patreon.OAuth(self.client_id, self.client_secret)
        tokens = oauth_client.get_tokens(request.query.code, self.callback)
        self.engine.logging.auth(tokens)
        access_token = tokens['access_token']
        
        return access_token, patreon.API(access_token)
        
    def getSession(self, request):
        """ Query patreon to return required user data and infos.
        This tests the pledge level. """
        token, client = self.getApiClient(request)
        
        user_response = client.fetch_user()   
        self.engine.logging.auth(user_response)
        json_data     = user_response.json_data
        user          = PatreonApi.getUserInfo(json_data)
        self.engine.logging.auth(user)
        result = {
            'sid'     : token,
            'user'    : user,
            'granted' : False
        }
        
        # test whitelist
        if user['id'] in self.whitelist:
            result['granted'] = True
            return result
        
        # test pledge
        amount = PatreonApi.getUserPledgeAmount(json_data)
        if amount >= self.min_pledge:
            result['granted'] = True
        
        return result


# ---------------------------------------------------------------------

class LoggingApi(object):

    def __init__(self, quiet, info_file, error_file, access_file, warning_file, stats_file, auth_file, stdout_only=False, loglevel='INFO'):
        self.log_format = logging.Formatter('[%(asctime)s at %(module)s/%(filename)s:%(lineno)d] %(message)s')
        
        # setup info logger
        self.info_logger = logging.getLogger('info_log')
        self.info_logger.setLevel(loglevel)
        
        if not stdout_only:
            self.linkFile(self.info_logger, info_file)
        elif not quiet:
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
        elif not quiet:
            self.linkStdout(self.access_logger)
        
        # setup warning logger
        self.warning_logger = logging.getLogger('warning_log')   
        self.warning_logger.setLevel(loglevel)
        
        if not stdout_only:
            self.linkFile(self.warning_logger, warning_file)
        elif not quiet:
            self.linkStdout(self.warning_logger)
        
        # setup stats logger
        self.stats_logger = logging.getLogger('stats_log')   
        self.stats_logger.setLevel(loglevel)
        
        # @NOTE: this log is required for `stats.py` and cannot be disabled
        self.linkFile(self.stats_logger, stats_file)
        
        # setup auth logger
        self.auth_logger = logging.getLogger('auth_log')
        self.auth_logger.setLevel(logging.INFO)
        
        if not stdout_only:
            self.linkFile(self.auth_logger, auth_file)
        elif not quiet:
            self.linkStdout(self.stats_logger)
        
        # link logging handles
        self.info    = self.info_logger.info
        self.error   = self.error_logger.error
        self.access  = self.access_logger.info
        self.warning = self.warning_logger.warning
        self.stats   = self.stats_logger.info
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

    def linkFile(self, target, fname):
        """Links the given logger to the provided filename."""
        handler = logging.FileHandler(fname, mode='a')
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
                    self.engine.notify_api(error_id, message)
                
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

