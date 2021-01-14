#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import unittest

from tests.token import TokenTest
from tests.scene import SceneTest
from tests.game import GameTest

from tests.example import ExampleTest

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
	#
	register(suite, ExampleTest)
	return suite

if __name__ == '__main__':
	runner = unittest.TextTestRunner()
	runner.run(suite())
