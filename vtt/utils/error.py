"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

import typing
import tempfile
import traceback
import json
import uuid

import bottle


IpQuerier = typing.Callable[[bottle.Request], str]
ErrorHandler = typing.Callable[[str, str], None]


def get_stacktrace() -> str:
    """Get exception traceback as a string."""
    with tempfile.TemporaryFile(mode='w+') as h:
        traceback.print_exc(file=h)
        h.seek(0)  # rewind after writing
        return h.read()


def get_cookie() -> dict:
    """Get HTTP cookies to a string."""
    return {key: value for key, value in bottle.request.cookies.items()}


def get_metadata(error: Exception) -> dict:
    """Get Exception Metadata as a string."""
    if hasattr(error, 'metadata'):
        # dump metadata that was fetched from the player cache instances earlier
        return error.metadata

    return {}


class ErrorDispatcher:

    def __init__(self, get_client_ip: IpQuerier, on_error: ErrorHandler) -> None:
        self.get_client_ip = get_client_ip
        self.on_error = on_error

    def fetch_report(self, error: Exception) -> tuple[str, str]:
        """Fetch and return an error-ID and error-message"""
        stacktrace = get_stacktrace()
        full_url = bottle.request.fullpath
        error_id = uuid.uuid1().hex
        client_ip = self.get_client_ip(bottle.request)

        cookies = get_cookie()
        metadata = get_metadata(error)

        data = {
            'error_id': error_id,
            'route_url': full_url,
            'client_ip': client_ip,
            'cookies': cookies,
            'metadata': metadata,
            'stacktrace': stacktrace
        }
        message = json.dumps(data, indent=4)

        return error_id, message

    def handle_error(self, error: Exception) -> None:
        error_id, message = self.fetch_report(error)

        self.on_error(error_id, message)

        # notify user about error
        if bottle.request.is_ajax:
            # cause handling in javascript
            bottle.abort(500, error_id)
        else:
            # custom error page
            bottle.redirect(f'/vtt/error/{error_id}')

    def plugin(self, func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except bottle.HTTPResponse as _:
                raise
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception as error:
                self.handle_error(error)

        return wrapper
