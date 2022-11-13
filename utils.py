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
            'patreon': 'data:image/png;base64,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',
            'auth0': 'data:image/png;base64,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'
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

    def parseProvider(self, url):
        # split username from url
        raw = base64.b64decode(url).decode('utf-8')
        provider = '-'.join(raw.split('|')[:-1])

        # split 'oauth2'-section from provider
        for s in ['-oauth2', 'oauth2-']:
            provider = provider.replace(s, '')

        return provider.lower()
    
    def getGmInfo(self, url):
        """ Query identity provider from the base64 url.
        Scene: <provider>|<id>
        but <provider> may include more '|'.
        """
        provider = self.parseProvider(url)

        return f'<img src="{self.favicons[provider]}" class="favicon" />'
    
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

    def __init__(self, quiet, info_file, error_file, access_file, warning_file, logins_file, auth_file, stdout_only=False, loglevel='INFO'):
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
        elif not quiet:
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

