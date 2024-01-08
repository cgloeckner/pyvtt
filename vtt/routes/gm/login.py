"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

import gevent

from bottle import *


def _login_callback(engine: any, provider: str):
    """Registers a callback url for oauth-login with the given provider."""

    def register_new_gm_account(session: any) -> 'GM':
        # create GM (username as display name, user-id as url)
        gm = engine.main_db.GM(
            name=session['name'],
            identity=session['identity'],
            metadata=session['metadata'],
            url=engine.main_db.GM.generate_uuid(),
            sid=engine.main_db.GM.generate_session(),
        )
        gm.post_setup()
        engine.main_db.commit()

        # add to cache and initialize database
        engine.cache.insert(gm)
        gm_cache = engine.cache.get(gm)

        # @NOTE: database creation NEEDS to be run from another
        # thread, because every bottle route has a db_session
        # active, but creating a database from within a db_session
        # isn't possible
        tmp = gevent.Greenlet(run=gm_cache.connect_db)
        tmp.start()
        try:
            tmp.get()
        except gevent.Timeout:
            # reraise greenlet Timeout exception to trigger proper error reporting
            raise

        return gm

    @get(f'/vtt/callback/{provider}')
    def gm_login_callback():
        client_ip = engine.get_client_ip(request)

        # query session from login auth
        session = engine.login_api.apis[provider].get_session(request.url)
        gm = engine.main_db.GM.select(lambda g: g.identity == session['identity']).first()
        if gm is None:
            gm = register_new_gm_account(session)

            engine.logging.access(f'GM created using external auth with name="{gm.name}" url={gm.url} by {client_ip}.')

        else:
            # create new session for already existing GM
            gm.sid = engine.main_db.GM.generate_session()
            gm.name = session['name']
            gm.metadata = session['metadata']

        gm.refresh_session(response)

        engine.logging.access(f'GM name="{gm.name}" url={gm.url} session refreshed using external auth by {client_ip}')

        engine.main_db.commit()
        # redirect to GM's game overview
        redirect('/')


def register(engine: any):

    # shared login page
    @get('/vtt/join')
    @view('join')
    def gm_login():
        return dict(engine=engine)

    if engine.login_api is not None:
        for provider in engine.login_api.apis:
            _login_callback(engine, provider)

    else:
        # non-auth login (fallback)
        @post('/vtt/join')
        def post_gm_login():
            client_ip = engine.get_client_ip(request)

            status = {
                'url': None,
                'error': ''
            }

            # test gm name (also as url)
            gm_name = request.forms.gmname
            if not engine.verify_url_section(gm_name):
                # contains invalid characters
                status['error'] = 'NO SPECIAL CHARS OR SPACES'
                engine.logging.warning(f'Failed GM login by {client_ip}: invalid name "{gm_name}".')
                return status

            name = gm_name[:20].lower().strip()
            if name in engine.gm_blacklist:
                # blacklisted name
                status['error'] = 'RESERVED NAME'
                engine.logging.warning(f'Failed GM login by {client_ip}: reserved name "{gm_name}".')
                return status

            if len(engine.main_db.GM.select(lambda g: g.name == name or g.url == name)) > 0:
                # collision
                status['error'] = 'ALREADY IN USE'
                engine.logging.warning(f'Failed GM login by {client_ip}: name collision "{gm_name}".')
                return status

            # create new GM (use GM name as display name and URL)
            sid = engine.main_db.GM.generate_session()
            gm = engine.main_db.GM(name=name, identity=name, url=name, sid=sid)
            gm.post_setup()
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
            except gevent.Timeout:
                # reraise greenlet Timeout exception to trigger proper error reporting
                raise

            expires = time.time() + engine.cleanup['expire']
            response.set_cookie('session', sid, path='/', expires=expires, secure=engine.has_ssl())

            engine.logging.access(f'GM created with name="{gm.name}" url={gm.url} by {client_ip}.')

            engine.main_db.commit()
            status['url'] = gm.url
            return status

    @get('/vtt/logout')
    def vtt_logout():
        # remove cookie
        response.set_cookie('session', '', path='/', max_age=1, secure=engine.has_ssl())
        # redirect default index
        redirect('/')
