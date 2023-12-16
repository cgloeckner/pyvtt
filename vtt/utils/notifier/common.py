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
    def onStart(self) -> None: ...
    def onCleanup(self, report: str) -> None: ...
    def onError(self, error_id: str, message: str) -> None: ...

