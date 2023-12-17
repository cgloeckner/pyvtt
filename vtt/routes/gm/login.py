"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

import gevent

from bottle import *


def _login_callback(engine, provider):
    """Registers a callback url for oauth-login with the given provider."""

    @get(f'/vtt/callback/{provider}')
    def gm_login_callback():
        # query session from login auth
        session = engine.login_api.providers[provider].get_session(request)
        if 'identity' not in session:
            redirect('/vtt/join')

        # test whether GM is already there
        gm = engine.main_db.GM.select(lambda g: g.identity == session['identity']).first()
        if gm is None:
            # create GM (username as display name, user-id as url)
            gm = engine.main_db.GM(
                name=session['name'],
                identity=session['identity'],
                metadata=session['metadata'],
                url=engine.main_db.GM.genUUID(),
                sid=engine.main_db.GM.genSession(),
            )
            gm.postSetup()
            engine.main_db.commit()

            # add to cache and initialize database
            engine.cache.insert(gm)
            gm_cache = engine.cache.get(gm)

            # @NOTE: database creation NEEDS to be run from another
            # thread, because every bottle route has an db_session
            # active, but creating a database from within a db_session
            # isn't possible
            tmp = gevent.Greenlet(run=gm_cache.connect_db)
            tmp.start()
            try:
                tmp.get()
            except:
                # reraise greenlet's exception to trigger proper error reporting
                raise

            engine.logging.access(
                'GM created using external auth with name="{0}" url={1} by {2}.'.format(gm.name, gm.url,
                                                                                        engine.getClientIp(
                                                                                            request)))

        else:
            # create new session for already existing GM
            gm.sid = engine.main_db.GM.genSession()
            gm.name = session['name']
            gm.metadata = session['metadata']

        gm.refreshSession(response)

        engine.logging.access(
            'GM name="{0}" url={1} session refreshed using external auth by {2}'.format(gm.name, gm.url,
                                                                                        engine.getClientIp(
                                                                                            request)))

        engine.main_db.commit()
        # redirect to GM's game overview
        redirect('/')


def register(engine):

    # shared login page
    @get('/vtt/join')
    @view('join')
    def gm_login():
        return dict(engine=engine)

    if engine.login_api is not None:
        for provider in engine.login_api.providers:
            _login_callback(engine, provider)

    else:
        # non-auth login (fallback)
        @post('/vtt/join')
        def post_gm_login():
            status = {
                'url'   : None,
                'error' : ''
            }

            # test gm name (also as url)
            gmname = request.forms.gmname
            if not engine.verifyUrlSection(gmname):
                # contains invalid characters
                status['error'] = 'NO SPECIAL CHARS OR SPACES'
                engine.logging.warning('Failed GM login by {0}: invalid name "{1}".'.format(engine.getClientIp(request), gmname))
                return status

            name = gmname[:20].lower().strip()
            if name in engine.gm_blacklist:
                # blacklisted name
                status['error'] = 'RESERVED NAME'
                engine.logging.warning('Failed GM login by {0}: reserved name "{1}".'.format(engine.getClientIp(request), gmname))
                return status

            if len(engine.main_db.GM.select(lambda g: g.name == name or g.url == name)) > 0:
                # collision
                status['error'] = 'ALREADY IN USE'
                engine.logging.warning('Failed GM login by {0}: name collision "{1}".'.format(engine.getClientIp(request), gmname))
                return status

            # create new GM (use GM name as display name and URL)
            sid = engine.main_db.GM.genSession()
            gm = engine.main_db.GM(name=name, identity=name, url=name, sid=sid)
            gm.postSetup()
            engine.main_db.commit()

            # add to cache and initialize database
            engine.cache.insert(gm)
            gm_cache = engine.cache.get(gm)

            # @NOTE: database creation NEEDS to be run from another
            # thread, because every bottle route has an db_session
            # active, but creating a database from within a db_session
            # isn't possible
            tmp = gevent.Greenlet(run=gm_cache.connect_db)
            tmp.start()
            try:
                tmp.get()
            except:
                # reraise greenlet's exception to trigger proper error reporting
                raise

            expires = time.time() + engine.cleanup['expire']
            response.set_cookie('session', sid, path='/', expires=expires, secure=engine.hasSsl())

            engine.logging.access('GM created with name="{0}" url={1} by {2}.'.format(gm.name, gm.url, engine.getClientIp(request)))

            engine.main_db.commit()
            status['url'] = gm.url
            return status

    @get('/vtt/logout')
    def vtt_logout():
        # remove cookie
        response.set_cookie('session', '', path='/', max_age=1, secure=engine.hasSsl())
        # redirect default index
        redirect('/')
