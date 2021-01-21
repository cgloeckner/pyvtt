#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import unittest

# testing orm.py
from tests.token import TokenTest
from tests.scene import SceneTest
from tests.game import GameTest
from tests.gm import GmTest

# testing utils.py
from tests.path_api import PathApiTest
from tests.logging_api import LoggingApiTest
from tests.fancy_url_api import FancyUrlApiTest

# testing engine.py
from tests.engine import EngineTest

# testing cache.py
from tests.engine_cache import EngineCacheTest
from tests.gm_cache import GmCacheTest
from tests.game_cache import GameCacheTest
from tests.cache_integration import CacheIntegrationTest


# ---------------------------------------------------------------------

def register(suite, testcase):
	""" Register all test methods of the given testcase class
	to the given suite.
	"""
	for method in dir(testcase):
		if method.startswith('test_'):
			suite.addTest(testcase(method))

def suite():
	""" Create the entire test suite.
	"""
	suite = unittest.TestSuite()
	
	register(suite, TokenTest)
	register(suite, SceneTest)
	register(suite, GameTest)
	register(suite, GmTest)
	
	register(suite, PathApiTest)
	register(suite, LoggingApiTest)
	register(suite, FancyUrlApiTest)
	
	register(suite, EngineTest)
	
	register(suite, EngineCacheTest)
	register(suite, GmCacheTest) 
	register(suite, GameCacheTest)
	register(suite, CacheIntegrationTest)
	
	return suite

if __name__ == '__main__':
	runner = unittest.TextTestRunner()
	runner.run(suite())
	
	untested = [
		'utils/EmailApi',
		'utils/PatreonApi',
		'utils/ErrorReporter',
		'server/VttServer'
	]
	
	print('')
	print('REMINDER: The following classes are not tested automatically:')
	for s in untested:
		print('\t{0}'.format(s))
	print('Make sure to test them manually')
