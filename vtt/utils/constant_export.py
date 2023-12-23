"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2022 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

import pathlib
import typing


# Exports Constants to a JavaScript-File to allow their use client-side, too
class ConstantExport(dict):

    def load_from_engine(self, engine: typing.Any) -> None:
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

    def save_to_memory(self) -> str:
        out = ''
        for key in self:
            raw = self[key]
            if isinstance(raw, str):
                raw = '"{0}"'.format(raw)
            elif isinstance(raw, bool):
                raw = 'true' if raw else 'false'
            out += f'var {key} = {raw};\n'
        return out

    def save_to_file(self, path: pathlib.Path) -> None:
        content = '/** DO NOT MODIFY THIS FILE. IT WAS CREATED AUTOMATICALLY. */\n'
        content += self.save_to_memory()
        with open(path, 'w') as h:
            h.write(content)
