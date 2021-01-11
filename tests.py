#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import sys, os, tempfile, pathlib

from utils import PathApi
from engine import Engine

if __name__ == '__main__':
	# start engine with temporary directory
	with tempfile.TemporaryDirectory() as tmpdirname:
		root  = pathlib.Path(tmpdirname)
		
		# pregenerate paths api for dummyfiles
		paths = PathApi(appname='pyvtt', root=root)
		for w in ['verbs', 'adjectives', 'nouns']:
			with open(paths.getFancyUrlPath() / '{0}.txt'.format(w), 'w') as h:
				h.write('demo')
		
		# load engine for unittest
		engine = Engine(argv=sys.argv, pref_dir=root)
		
		# TODO: trigger unit tests using 'webtest'


