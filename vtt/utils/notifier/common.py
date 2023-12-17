"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

import typing


class Notifier(typing.Protocol):
    def login(self) -> None: ...
    def on_start(self) -> None: ...
    def on_cleanup(self, report: any) -> None: ...
    def on_error(self, error_id: str, message: str) -> None: ...
