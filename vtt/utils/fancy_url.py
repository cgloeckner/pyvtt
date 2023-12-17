"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

import os
import random

from .path_api import PathApi


class FancyUrlApi:

    def __init__(self, paths: PathApi) -> None:
        self.paths = paths
        self.parts = dict()

        # create default words if necessary
        v = ['be', 'have', 'do', 'say', 'go', 'get', 'make', 'know', 'think', 'take']
        a = ['able', 'bad', 'best', 'better', 'big', 'black', 'certain', 'clear', 'different', 'early', 'easy']
        n = ['area', 'book', 'business', 'case', 'child', 'company', 'country', 'day', 'eye', 'fact']
        for t in [('verbs', v), ('adjectives', a), ('nouns', n)]:
            p = self.paths.get_fancy_url_path(t[0])
            if not os.path.exists(p):
                with open(p, mode='w') as h:
                    h.write('\n'.join(t[1]))

        # load word lists
        for p in ['verbs', 'adjectives', 'nouns']:
            self.parts[p] = self.load(p)

    def load(self, filename: str) -> list[str]:
        # load words
        path = self.paths.get_fancy_url_path(filename)
        with open(path, mode='r') as h:
            content = h.read()
        words = content.split('\n')
        if words[-1] == '':
            # ignore empty line at eof
            words.pop()

        # test words not being empty
        for word in words:
            assert (word != '')

        return words

    def __call__(self) -> str:
        """ Generate a random url using <verb>-<adverb>-<noun>.
        """
        results = []
        for part in self.parts:
            line = self.parts[part]
            word = random.choice(line)
            results.append(word)
        return '-'.join(results)
