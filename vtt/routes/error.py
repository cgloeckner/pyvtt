"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

from bottle import *


def register(engine):

    @error(401)
    @view('error401')
    def error401(error):
        return dict(engine=engine)

    @error(404)
    @view('error404')
    def error404(error):
        return dict(engine=engine)

    @get('/vtt/error/<error_id>')
    @view('error500')
    def caught_error(error_id):
        return dict(engine=engine, error_id=error_id)
