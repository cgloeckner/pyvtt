#!/usr/bin/python3
# -*- coding: utf-8 -*-

__author__ = "Christian Glöckner"

import unittest

import orm

def register(suite, class_):
	"""Register all testcase methods of the given test case class to the given
	suite
	"""
	for method in dir(class_):
		if method.startswith('test_'):
			suite.addTest(class_(method))

def suite():
	"""Create whole test suite
	"""
	suite = unittest.TestSuite()
	register(suite, orm.Tests)
	return suite

if __name__ == '__main__':
	orm.db.bind('sqlite', ':memory:', create_db=True)
	orm.db.generate_mapping(create_tables=True)
	
	runner = unittest.TextTestRunner()
	runner.run(suite())
