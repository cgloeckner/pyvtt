#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

from engine import Engine


__author__ = 'Christian Glöckner'
__licence__ = 'MIT'


if __name__ == '__main__':
	engine = Engine(argv=['--quiet'])     
	print('{0} cleanup script started.'.format(engine.title))
	engine.cleanup() 
	print('Done.')

