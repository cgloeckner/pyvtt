#!/usr/bin/python3

from engine import Engine

if __name__ == '__main__':
	engine = Engine()     
	print('{0} cleanup script started.'.format(engine.title))
	
	engine.cleanup()          
	print('Done.')
