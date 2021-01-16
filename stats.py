#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import os, pathlib, json
from datetime import datetime

from pony.orm import db_session

from engine import Engine


__author__ = 'Christian Glöckner'
__licence__ = 'MIT'


def formatBytes(b):
	if b > 1024 * 1024:
		return '{0} MiB  '.format(int(b / (1024*1024)))
	if b > 1024:
		return '{0} KiB  '.format(int(b / 1024))
	return '{0} Bytes'.format(b)

def disk_report(engine):
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
	
	print('GMs, Games, Files, Used Disk Space of {0}'.format(engine.title))
	print('\n   Space Used   | Number of Files |  Number of Games    | GM')
	print('-' * 80)
	games = 0 
	sizes = 0
	files = 0
	
	# per GM
	for gm in listing:
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
	print('{0} |{1} files |{2} games \t| {3} GMs'.format(sizes, files, games, len(listing)))


# ---------------------------------------------------------------------

class Login(object):
	
	def __init__(self, is_gm, timeid, country, ip, num_players):
		self.is_gm       = is_gm
		self.timeid      = timeid
		self.country     = country
		self.ip          = ip
		self.num_players = num_players
		
	def __repr__(self):
		return '<Login|{0}|{1}|{2}|{3}|{4}>'.format(self.is_gm, self.timeid, self.country, self.ip, self.num_players)
		
	def getDatetime(self):
		return datetime.fromtimestamp(self.timeid)

def print_stats(title, data, key, func):
	print(title)
	print('-' * len(title))
	# get total
	total = 0
	for h in data:
		l = func(data[h][key])
		if l > 0:
			total += l
	# print percentages
	for h in data:
		l = func(data[h][key])
		if l > 0:
			n = int(100 * l / total)
			perc = '{0}'.format(n)
			if len(perc) == 1:
				perc = '  ' + perc
			elif len(perc) == 2:
				perc = ' ' + perc
			print (' {0}\t| {2}% {1} {3}'.format(h, '*' * n, perc, n))
	print('Total: {0}'.format(total))

def stats_report(engine):
	# parse stats from logfile
	data = list()
	fname = engine.paths.getLogPath('stats')
	with open(fname, 'r') as h:
		content = h.read()
		for line in content.split('\n'):
			if line == '':
				continue
			data.append(Login(*json.loads(line)))
	
	# build statistics
	per_hours   = dict()
	per_country = dict()
	for h in range(24):
		per_hours[h] = {
			'logins'  : 0,
			'ips'     : set(),
			'players' : 0
		}
	
	for l in data:
		hour = l.getDatetime().hour
		per_hours[hour]['logins'] += 1
		per_hours[hour]['ips'].add(l.ip)
		per_hours[hour]['players'] = max(per_hours[hour]['players'], l.num_players)
		
		if l.country not in per_country:
			per_country[l.country] = {
				'logins' : 0,
				'ips'    : set()
			}
		per_country[l.country]['logins'] += 1
		per_country[l.country]['ips'].add(l.ip)
		  
	print()
	print_stats('Logins per Hour (UTC)', per_hours, 'logins', lambda k: k)
	print()
	print_stats('IPs per Hour (UTC)', per_hours, 'ips', lambda k: len(k))
	print()
	print_stats('Players per Hour (UTC)', per_hours, 'players', lambda k: k) 
	print()
	
	print_stats('Logins per Country', per_country, 'logins', lambda k: k)
	print()
	print_stats('IPs per Country', per_country, 'ips', lambda k: len(k))


if __name__ == '__main__':
	engine = Engine(argv=['--quiet'])
	
	disk_report(engine)
	
	print('*' * 80)
	
	stats_report(engine)

