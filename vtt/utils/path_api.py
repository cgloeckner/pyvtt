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


# API for providing local harddrive paths
class PathApi(object):

    def __init__(self, appname, pref_root=None, app_root=pathlib.Path('..')) -> None:
        """ Uses given root or pick standard preference directory. """
        self.app_root = app_root
        if pref_root is None:
            # get preference dir
            p = pathlib.Path.home()
            if sys.platform.startswith('linux'):
                p = p / ".local" / "share"
            else:
                raise NotImplementedError('only linux supported yet')

            pref_root = p

        self.pref_root = pref_root / appname

        # make sure paths exists
        self.ensure(self.pref_root)
        self.ensure(self.getExportPath())
        self.ensure(self.getGmsPath())
        self.ensure(self.getFancyUrlPath())
        self.ensure(self.getStaticPath())
        self.ensure(self.getAssetsPath())
        self.ensure(self.getClientCodePath())

    def ensure(self, path) -> None:
        if not os.path.isdir(path):
            os.mkdir(path)

    # Engine paths

    def getStaticPath(self, default: bool = False) -> pathlib.Path:
        root = self.app_root if default else self.pref_root
        return root / 'static'

    def getAssetsPath(self, default: bool = False) -> pathlib.Path:
        return self.getStaticPath(default=default) / 'assets'

    def getClientCodePath(self) -> pathlib.Path:
        return self.getStaticPath() / 'client'

    def getLogPath(self, fname: str) -> pathlib.Path:
        return self.pref_root / '{0}.log'.format(fname)

    def getSettingsPath(self) -> pathlib.Path:
        return self.pref_root / 'settings.json'

    def getMainDatabasePath(self) -> pathlib.Path:
        return self.pref_root / 'main.db'

    def getConstantsPath(self) -> pathlib.Path:
        return self.getClientCodePath() / 'constants.js'

    def getSslPath(self) -> pathlib.Path:
        return self.pref_root / 'ssl'

    def getExportPath(self) -> pathlib.Path:
        return self.pref_root / 'export'

    def getGmsPath(self, gm=None) -> pathlib.Path:
        p = self.pref_root / 'gms'
        if gm is not None:
            p /= gm
        return p

    def getFancyUrlPath(self, fname=None) -> pathlib.Path:
        p = self.pref_root / 'fancyurl'
        if fname is not None:
            p /= '{0}.txt'.format(fname)
        return p

    # GM- and Game-relevant paths

    def getDatabasePath(self, gm) -> pathlib.Path:
        return self.getGmsPath(gm) / 'gm.db'

    def getGamePath(self, gm, game) -> pathlib.Path:
        return self.getGmsPath(gm) / game

    def getMd5Path(self, gm, game) -> pathlib.Path:
        return self.getGamePath(gm, game) / 'gm.md5'

