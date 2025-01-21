"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

import os
import pathlib
import sys


# API for providing local hard drive paths
class PathApi:

    def __init__(self, appname: str, pref_root: pathlib.Path | None = None, app_root=pathlib.Path('..')) -> None:
        """ Uses given root or pick standard preference directory. """
        self.app_root = app_root
        self.pref_root = pref_root
        if pref_root is None:
            # use current working directory instead
            self.pref_root = pathlib.Path.cwd() / 'data'
        
        self.pref_root /= appname

        # make sure paths exists
        self.ensure(self.pref_root)
        self.ensure(self.get_export_path())
        self.ensure(self.get_gms_path())
        self.ensure(self.get_fancy_url_path())
        self.ensure(self.get_static_path())
        self.ensure(self.get_assets_path())
        self.ensure(self.get_client_code_path())

    @staticmethod
    def ensure(path: pathlib.Path) -> None:
        if not path.is_dir():
            path.mkdir(parents=True)

    # Engine paths

    def get_static_path(self, default: bool = False) -> pathlib.Path:
        root = self.app_root if default else self.pref_root
        return root / 'static'

    def get_assets_path(self, default: bool = False) -> pathlib.Path:
        return self.get_static_path(default=default) / 'assets'

    def get_client_code_path(self) -> pathlib.Path:
        return self.get_static_path() / 'client'

    def get_log_path(self, filename: str) -> pathlib.Path:
        return self.pref_root / '{0}.log'.format(filename)

    def get_main_database_path(self) -> pathlib.Path:
        return self.pref_root / 'main.db'

    def get_constants_path(self) -> pathlib.Path:
        return self.get_client_code_path() / 'constants.js'

    def get_ssl_path(self) -> pathlib.Path:
        return self.pref_root / 'ssl'

    def get_export_path(self) -> pathlib.Path:
        return self.pref_root / 'export'

    def get_gms_path(self, gm: str | None = None) -> pathlib.Path:
        p = self.pref_root / 'gms'
        if gm is not None:
            p /= gm
        return p

    def get_fancy_url_path(self, filename: str | None = None) -> pathlib.Path:
        p = self.pref_root / 'fancyurl'
        if filename is not None:
            p /= '{0}.txt'.format(filename)
        return p

    # GM- and Game-relevant paths

    def get_database_path(self, gm: str) -> pathlib.Path:
        return self.get_gms_path(gm) / 'gm.db'

    def get_game_path(self, gm: str, game: str) -> pathlib.Path:
        return self.get_gms_path(gm) / game

    def get_md5_path(self, gm: str, game: str) -> pathlib.Path:
        return self.get_game_path(gm, game) / 'gm.md5'
