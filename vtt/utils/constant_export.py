"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2022 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'


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
        import vtt.orm as orm
        self['MAX_SCENE_WIDTH'] = orm.MAX_SCENE_WIDTH
        self['MAX_SCENE_HEIGHT'] = orm.MAX_SCENE_HEIGHT
        self['MIN_TOKEN_SIZE'] = orm.MIN_TOKEN_SIZE
        self['MAX_TOKEN_SIZE'] = orm.MAX_TOKEN_SIZE
        self['MAX_TOKEN_LABEL_SIZE'] = orm.MAX_TOKEN_LABEL_SIZE

        self['MAX_TOKEN_FILESIZE'] = engine.file_limit['token']
        self['MAX_BACKGROUND_FILESIZE'] = engine.file_limit['background']
        self['MAX_GAME_FILESIZE'] = engine.file_limit['game']
        self['MAX_MUSIC_FILESIZE'] = engine.file_limit['music']
        self['MAX_MUSIC_SLOTS'] = engine.file_limit['num_music']

        self['SUGGESTED_PLAYER_COLORS'] = engine.playercolors

        self.saveToFile(engine.paths.getConstantsPath())

