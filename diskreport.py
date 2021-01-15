#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import os, pathlib

from pony.orm import db_session

from engine import Engine


__author__ = 'Christian Glöckner'
__licence__ = 'MIT'


def queryReport(engine):
	listing = list()
	with db_session:
		for gm in engine.main_db.GM.select():
			gm_cache = engine.cache.get(gm)
			report = dict()
			report['name']  = '{0}#{1}'.format(gm.name, gm.url)
			report['games'] = 0
			total_sizes     = os.path.getsize(engine.paths.getDatabasePath(gm.url))
			total_files     = 1 # gm.db
			# query all games by this gm
			for game in gm_cache.db.Game.select():
				# fetch image metadata
				game_path = engine.paths.getGamePath(gm.url, game.url)
				imglist   = os.listdir(game_path)
				imgsize   = 0
				for f in imglist:
					imgsize += os.path.getsize(game_path / f)
				report['games'] += 1
				total_files += len(imglist)
				total_sizes += imgsize
			report['total_files'] = total_files
			report['total_sizes'] = total_sizes
			listing.append(report)
	return listing

def formatBytes(b):
	if b > 1024 * 1024:
		return '{0} MiB  '.format(int(b / (1024*1024)))
	if b > 1024:
		return '{0} KiB  '.format(int(b / 1024))
	return '{0} Bytes'.format(b)


if __name__ == '__main__':
	engine = Engine(argv=['--quiet'])
	
	report = queryReport(engine)
	
	print('GMs, Games, Files, Used Disk Space of {0}'.format(engine.title))
	print('\n   Space Used   | Number of Files |  Number of Games    | GM')
	print('-' * 80)
	games = 0 
	sizes = 0
	files = 0
	
	# per GM
	for gm in report:
		total_sizes = formatBytes(gm['total_sizes'])
		while len(total_sizes) < 15:
			total_sizes = ' ' + total_sizes
		total_files = str(gm['total_files'])
		while len(total_files) < 10:
			total_files = ' ' + total_files
		total_games = str(gm['games'])
		while len(total_games) < 10:
			total_games = ' ' + total_games
		print('{0} |{1} files |{2} games \t| {3}'.format(total_sizes, total_files, total_games, gm['name']))
		
		games += gm['games']
		sizes += gm['total_sizes']
		files += gm['total_files']
	
	# total
	print('=' * 5 + '~ TOTAL ~' + '=' * 65)
	
	sizes = formatBytes(sizes)
	while len(sizes) < 15:
		sizes = ' ' + sizes
	files = str(files)
	while len(files) < 10:
		files = ' ' + files
	games = str(games)
	while len(games) < 10:
		games = ' ' + games
	print('{0} |{1} files |{2} games \t| {3}'.format(sizes, files, games, gm['name']))
	

