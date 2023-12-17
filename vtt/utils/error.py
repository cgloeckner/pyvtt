"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

import tempfile
import traceback
import uuid

import bottle


# @NOTE: this class is not covered in the unit tests but during integration test
class ErrorReporter:

    def __init__(self, engine: any) -> None:
        self.engine = engine

    @staticmethod
    def get_stacktrace() -> str:
        # fetch exception traceback
        with tempfile.TemporaryFile(mode='w+') as h:
            traceback.print_exc(file=h)
            h.seek(0)  # rewind after writing
            return h.read()

    def plugin(self, func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except bottle.HTTPResponse as _:
                raise
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception as error:
                # fetch stacktrace and other debugging data
                stacktrace = self.get_stacktrace()
                error_id = uuid.uuid1().hex
                full_url = bottle.request.fullpath
                client_ip = self.engine.getClientIp(bottle.request)

                # dump cookies
                cookies = ''
                for key in bottle.request.cookies.keys():
                    cookies += '\t{0} : {1}\n'.format(key, bottle.request.cookies[key])
                if cookies == '':
                    cookies = '{}'
                else:
                    cookies = '{\n' + cookies + '}'

                # dump metadata (e.g. in case of websocket error)
                meta_dump = ''
                if hasattr(error, 'metadata'):
                    data = error.metadata
                    for key in data:
                        meta_dump += '\t{0} : {1}\n'.format(key, data[key])
                    if meta_dump == '':
                        meta_dump = '{}'
                    else:
                        meta_dump = '{\n' + meta_dump + '}'

                message = (f'Error ID  = #{error_id}\n'
                           f'Route URL = {full_url}\n'
                           f'Client-IP = {client_ip}\n'
                           f'Cookies   = {cookies}\n'
                           f'Metadata   = {meta_dump}\n\n{stacktrace}')

                # log error and notify developer
                self.engine.logging.error(message)
                if self.engine.notify_api is not None:
                    self.engine.notify_api.on_error(error_id, message)

                # notify user about error
                if bottle.request.is_ajax:
                    # cause handling in javascript
                    bottle.abort(500, error_id)
                else:
                    # custom error page
                    bottle.redirect('/vtt/error/{0}'.format(error_id))

        return wrapper
