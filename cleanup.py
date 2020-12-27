#!/usr/bin/python3

from orm import engine, db

if __name__ == '__main__':
	# bootup engine
	db.bind('sqlite', str(engine.data_dir / 'data.db'), create_db=False)
	db.generate_mapping(create_tables=False)
	engine.setup(['--debug']) # to force output to stdout
	
	# trigger cleanup
	print('{0} cleanup script started.'.format(engine.title))
	engine.cleanup()
	print('Done.')
