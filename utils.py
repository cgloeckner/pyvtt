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

from gevent import lock

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


# ---------------------------------------------------------------------


# @NOTE: this class is not covered in the unit tests because it depends too much on external resources
class GoogleApi(BaseLoginApi):

    def __init__(self, engine, **data):
        super().__init__('google', engine, **data)

        if engine.debug:
            # accept non-https for testing oauth (e.g. localhost)
            os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    
    def getAuthUrl(self):
        """ Generate google-URL to access in order to fetch data. """
        # create auth flow session
        f = Flow.from_client_config(
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

        auth_url, state = f.authorization_url()
        self.saveSession(state, f)
        
        return auth_url
        
    def getSession(self, request):
        """ Query google to return required user data and infos."""  
        state = BaseLoginApi.parseStateFromUrl(request.url)

        # fetch token
        f = self.loadSession(state)
        f.fetch_token(authorization_response=bottle.request.url)
        creds = f.credentials
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
        self.login_caption   = 'Click to Login'
        self.auth_endpoint   = f'https://{data["domain"]}/authorize'
        self.logout_endpoint = f'https://{data["domain"]}/v2/logout'
        self.token_endpoint  = f'https://{data["domain"]}/oauth/token'

        self.logout_callback = engine.getUrl()
        
        if engine.debug:
            # accept non-https for testing oauth (e.g. localhost)
            os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        self.favicons = {
            'google': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAYAAABXAvmHAAAFC0lEQVRoQ+1Ya0xbdRT/n3tboAOEMkBoNTrd4gws2dIVTFgmMsysD4bM+kgcfFBnomNf1PjBpL24GI0fl/ltugU3IkWG8zGYUFpdkARwC8T5IBp84DBlPDakpaW9f88lMBvobf/39pJlSe+XPu45v9/5nXP+TyC3+AO3ePwkJeBmVzBVgVQFksxAqoWSTGDS7ppX4K9qyzZe5MtFoKUEIA9Emo6T9SShdBKAG9Yv6N0FfX1zSUe+DKCJgLHK7bl6nf4QUFKPuFviBYeEi5SQbwih75vdQ93JCklKAAYCE3ush/HTgYHkKQ6Gkj6OkpeLPYOXFfsmW4EJ244CMaRrQZxqteTLfvMAcNDUMyBhKX5UVeDPh3eYsM97sAD3K2aM4YACzhUb76qBtraIUjzFAiYrKrJDGaF+JCpRSiZj3+VPm6nd0vlrUA2eYgFXqq0uSok9DpkfZ51WItJuoPwo0YfniUjyqcg9AEDsOF7KonzPhyKZtZu83gU1wUs+igSM7yl7HAj9Qo4M3zWTCH3N5P3+qpzNMsZxAnQ4FM7al0zwigRQgXC+X0rbwz5DbYzgKM7zh829Q8dYMvn7Xksxfz1t9s7+/gCLfYJpmQ1ivpOvAQJnA73m/uDFwp3YCvobngBN5p4BgQ1JWyvmFvJ36l24+Cz1fngse2TuzOYiQkkh/rxoyru7TM0MooUUJgHURfiFbN0UZj1nhZT69b5rJ7aOk4D+iMk98JkWwajBYBIQPJ+2NSKKP60hiMCUYaiiCARvWI68qmmmESjuixQ+HIk0dQsFVxK5MQmYP8c/gYvN56vB0LnLYAvb4pFUCbNfYes9miiQNdgc3e125F1I5MckINDFH6AUmtcKoMcNtshL6yGAAjzlcea2r6sAnDs/zLRFXlwXAYS84BGMH2ki4Ka0EMCzbmduqyYCZAcxIVMNc0/e3va0/CZM7RigHKn0OIx4boj/MI0BaRr1Z+um0fi2FTiRgM9x3frHtwumd4YaPj0rR1Mp+LLC6Wn/L3pRhplBgEUi/ox/Faz2X9SHTRfeKpjQRIAEEr2Q/SvqhxtmKwsnxQ3F0kK2KZ0ri1cF2SlWmNmN79ZkGdebMez/exIFL71nqoBkuDIOLoeN3zVe22UNU+5GVnGX6Rx8vv1tFsIVG7uL8ld/nPViALti+B3rFYyNLHjMAqTN3Lul29vPBO6V2cyRxqH69g9YSHFdABwbR9H2UGx7rrxXyBlgwWIWIIFZPq57DDd0X8oBUyAn+Yj4+kBDx5ScTfmpujt00/veTJ+ukQmeeDD7VSzBK2qhFcCdzfs/wcZ7Jg7BPB54WjgCXZRERoHn/KJIc/HGogTFP4Ii69A3gw9s9myYeKMCDz1pUVgRjiPWHofx0roJKHHZswxBUTpSKt7frA4KRMMPmeNOI7eYb5beoTiHx2k8whq8qgpITtYT9iKqE7/Gr9uUkMW0pTBt+Ofg3zq/deRBklsvCCAqwVQ0BqKBLS3P5XNi6BS2y14lhDFsMWD+vazfWp1eAWR3tXIcqgUsAVICltN1eCMHTvy1UYWQMSDiK4MHOrpU+C65JCdgmdXisudAkL6KiqSrxfsSBIPrFLmE/X402zx12vuQ/FmCRZQmAqKJrCf3l1AdKcfq4CCnG7FIGbjQLV3uYr5GQ1R0j9R3+FiCY7HRXAALqZY2KQFaZlMNVqoCarKmpU+qAlpmUw1WqgJqsqalz38ZKr9AQ4SmQAAAAABJRU5ErkJggg==',
            'discord': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAYAAABXAvmHAAAEzElEQVRoQ+1ZXWgUVxQ+d3aTTakmVmpcG/wpxbYWqYUqtcWnFqPWH/pj+lKUTWZ3DYFFUmjeIksRCtpWaWqo+5NY/15ixYpagqWFQuhDtS30oS1CLFFTk6oEFVm77h6/u+yk42RnstncXV3YgSUz997znfOdc+bcMzeCyvwSZW4/VQg87Ag6RqDNx96km3YS0yYYOqekxjKNIj++YUGdsZgYsdNtSyAY5Hmcop8guLCkhk9U9jdIrLQjYUsg4OcYPK8/ZOMN9fujcdGayxZ7AjqPljxt7L01AgLeqRJIQ+BRqVIMAtpUCfAjkj4ZM0AgpzOdUqhCQGUEKxHIw5sJrDmHnBxF7r1tUwDOYNyN33L8ZueBOb6kmBH4DUbvTgsa05i2onQ9I5gugMQwtN/Aq5fC3yfw7MV9A/aWi9iY9mtpqoVMO2Q35kOkKASYqUNz03GYuA5GjJCLTkci4o6TQaH3uTbhobUo0B5XFfWnk7QC5A5Jkk5y6gkwfd+wgNYMD9MsGH0tHy9a17S2cr3XS9cuD1EnohMuLQGNNkaj4lQhhltlmpt5jlujIYzX2OEpjQDydvCp+bQ4HBZyt1ZyBXQ+CKAtpSEgaHckJjqUWJ4FCbTwJtk+l4QA3L4qHhcDKgm0N/Fjt2vpX2A+ngtXZQrdGLtJ9X19QpbH8autjWck71InvLgYZTQeiYvT/8+yCPophKq1HmO/VnloZ3e3uG011K/zSbuyqo6AoO+iMbHaqhw5vA9jbdnxeymmpT094i/5HNR5G0rll4YM7mOxuAhYMYJ+7gTJj4odgU/gjQ8nEGjhAXj/tfFxps3RHvG1fEZ+92Fus2nuT8wtyYFh+x6oiwDRVoDJjeeBCxHYjoG9chAevupJ0tJ9B8X1LIEPQOBTUwS+QgR8VoxWHy9KuehiUSOANqAR36dncynZpvMbmH+WNDqBze0fY004zG5sVjtAYh1y/HxNgjq6joibVoxQiD2JOyR7qgmXsgig8r8c6RW/GBqk0q4ucTeX0snGmprYJdeYCwIiKV/uCZVIGQF4+AVE4A/DOJxePM/36M2qNB3tPiCuTma0nJeGz5pJb7FGAljHTJHSrlzKNIFzrTjKCAB4QLio0dy06TovRCf6MVJkHnqafuwTZ1MpGurtFbKuk8/HNdXVVI+xZS5Br3OaXsS6LpTaE2ZDcRLyOV6gUFFTKAt+HrtAc+SA+P0BA3T+DM/tprH/cC/Ta+b4GNPPY7foVXPaZHohF30B49+zi6DKCBg6krg5A6V9OC4YlC8vqk8vxvI5ydiDd+lw2kXzIb8BAk2Qq3NKv2IQyCfdla2pEFDmygKBKhEo0HHKxAqJQM4dUZlFBpCgK6hEDZPhFkKgH6CNkwErmP8hU46JdjmV4CkTCDbzK9jqfwRotQIjnSCSaO6eTNRk2u0Ifpn+yHpNmYAECLZwIzYoCVrU/9JAx7voiY77/fwOvuaOQp9HCQEJIhuvujp6CTun48HTdKKEb9NBfL0NSgzZkqOXkj3SDDNmQRGYjlHTkQ0EeAVO+06hKak3cMqKgDQa6fQ0Otxv0V89J5/LjoA0Gm36bDSK8qxoVVkSkCSyn5mHQCBnq51P6zuddFYiKwuJ9RzKAC4LAk5eKHsC9wFb2OhA4cB92gAAAABJRU5ErkJggg==',
            'patreon': 'data:image/png;base64,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'
        }

    def getAuthUrl(self):
        """ Generate external oauth URL to access in order to fetch data. """
        # create session, redirect uri and state
        s = OAuth2Session(
            client_id=self.client_id,
            client_secret=self.client_secret,
            scope='openid profile',
            redirect_uri=self.callback
        )
        uri, state = s.create_authorization_url(self.auth_endpoint)
        self.saveSession(state, s)
        
        return uri
    
    def getLogoutUrl(self):
        return f'{self.logout_endpoint}?client_id={self.client_id}&returnTo={self.logout_callback}'
     
    def getGmInfo(self, url):
        """ Query identity provider from the base64 url.
        Scene: <provider>|<id>
        but <provider> may include more '|'.
        """
        # split username from url
        raw = base64.b64decode(url).decode('utf-8')
        provider = '-'.join(raw.split('|')[:-1])

        # split 'oauth2'-section from provider
        for s in ['-oauth2', 'oauth2-']:
            provider = provider.replace(s, '')

        return f'<img src="{self.favicons[provider.lower()]}" class="favicon" />'
    
    def getSession(self, request):
        """ Query google to return required user data and infos."""
        state = BaseLoginApi.parseStateFromUrl(request.url)

        # fetch token
        try:
            s = self.loadSession(state)
        except KeyError:
            return {'granted': False}
        
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
        print(data)

        # create base64 userid from subscription
        userid = base64.urlsafe_b64encode(data['sub'].encode('utf-8')).decode('utf-8')

        # create login data
        result = {
            'sid'  : data['sid'],
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

