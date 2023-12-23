"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import tempfile
import unittest
import pathlib

from vtt import utils, orm


class ConstantExportTest(unittest.TestCase):
    
    def setUp(self):            
        # create temporary directory
        self.tmp_file = tempfile.NamedTemporaryFile()
        
    def tearDown(self):
        del self.tmp_file

    def test_load_from_engine(self):
        class MockEngine:
            file_limit: dict[str, int] = {
                'token': 5,
                'background': 25,
                'game': 40,
                'music': 6,
                'num_music': 7
            }
            playercolors: list[str] = ['#ff0000', '#00ff00', '#0000ff']

        mock_engine = MockEngine()

        e = utils.ConstantExport()
        e.load_from_engine(mock_engine)

        self.assertEqual(e['MAX_SCENE_WIDTH'], orm.MAX_SCENE_WIDTH)
        self.assertEqual(e['MAX_SCENE_HEIGHT'], orm.MAX_SCENE_HEIGHT)
        self.assertEqual(e['MIN_TOKEN_SIZE'], orm.MIN_TOKEN_SIZE)
        self.assertEqual(e['MAX_TOKEN_SIZE'], orm.MAX_TOKEN_SIZE)
        self.assertEqual(e['MAX_TOKEN_LABEL_SIZE'], orm.MAX_TOKEN_LABEL_SIZE)

        self.assertEqual(e['MAX_TOKEN_FILESIZE'], 5)
        self.assertEqual(e['MAX_BACKGROUND_FILESIZE'], 25)
        self.assertEqual(e['MAX_GAME_FILESIZE'], 40)
        self.assertEqual(e['MAX_MUSIC_FILESIZE'], 6)
        self.assertEqual(e['MAX_MUSIC_SLOTS'], 7)

        self.assertEqual(e['SUGGESTED_PLAYER_COLORS'], mock_engine.playercolors)

    def test_saveToMemory(self):
        e = utils.ConstantExport()
        e['test'] = 'foo'
        e['bar'] = 42
        e['number'] = 3.14     
        e['thing'] = True
        e['other'] = False

        dumped = e.save_to_memory()
        expected = ('var test = "foo";\n'
                    'var bar = 42;\n'
                    'var number = 3.14;\n'
                    'var thing = true;\n'
                    'var other = false;\n')
        self.assertEqual(dumped, expected)

    def test_saveToFile(self):
        e = utils.ConstantExport()
        e['test'] = 'foo'
        e['bar'] = 42
        e['number'] = 3.14     
        e['thing'] = True
        e['other'] = False

        e.save_to_file(pathlib.Path(self.tmp_file.name))

        expected = ('/** DO NOT MODIFY THIS FILE. IT WAS CREATED AUTOMATICALLY. */'
                    '\n') + e.save_to_memory()
        with open(self.tmp_file.name, 'r') as h:
            content = h.read()
        self.assertEqual(content, expected)
