#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import sys, os, pathlib, json
from datetime import datetime

from pony.orm import db_session

from utils import PathApi


__author__ = 'Christian Glöckner'
__licence__ = 'MIT'


def formatBytes(b):
	if b > 1024 * 1024:
		return '{0} MiB  '.format(int(b / (1024*1024)))
	if b > 1024:
		return '{0} KiB  '.format(int(b / 1024))
	return '{0} Bytes'.format(b)

def disk_report(paths):
	listing = list()
	with db_session:
		gms_path = paths.getGmsPath()
		# query all GMs
		for gm_url in os.listdir(gms_path):
			report = dict()
			report['name']  = '#{0}'.format(gm_url)
			report['games'] = 0
			total_sizes     = os.path.getsize(paths.getDatabasePath(gm_url))
			total_files     = 1 # gm.db
			games_path = paths.getGmsPath(gm_url)
			# query all games by this GM
			for game_url in os.listdir(games_path):
				if not os.path.isdir(games_path / game_url):
					continue
				img_path = paths.getGamePath(gm_url, game_url)
				imglist  = os.listdir(img_path)
				imgsize  = 0
				# query all images at this game
				for f in imglist:
					imgsize += os.path.getsize(img_path / f)
				report['games'] += 1
				total_files += len(imglist)
				total_sizes += imgsize
			report['total_files'] = total_files
			report['total_sizes'] = total_sizes
			listing.append(report)
	return listing
	
def print_disk(listing):
	out =  'GMs, Games, Files, Used Disk Space\n'
	out += '\n   Space Used   | Number of Files |  Number of Games    | GM\n'
	out += '-' * 80 + '\n'
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
		out += '{0} |{1} files |{2} games \t| {3}\n'.format(total_sizes, total_files, total_games, gm['name'])
		
		games += gm['games']
		sizes += gm['total_sizes']
		files += gm['total_files']
	
	# total
	out += '=' * 5 + '~ TOTAL ~' + '=' * 65 + '\n'
	
	sizes = formatBytes(sizes)
	while len(sizes) < 15:
		sizes = ' ' + sizes
	files = str(files)
	while len(files) < 10:
		files = ' ' + files
	games = str(games)
	while len(games) < 10:
		games = ' ' + games
	out += '{0} |{1} files |{2} games \t| {3} GMs\n'.format(sizes, files, games, len(listing))
	
	return out


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

def print_stats(title, data, key, func, rowfunc):
	out = title + '\n'
	out += '-' * len(title) + '\n'
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
			out += ' {0}\t| {2}% {1} {3}\n'.format(rowfunc(h), '*' * n, perc, l)
	out += 'Total: {0}\n'.format(total)
	return out

def stats_report(paths):
	# parse stats from logfile
	data = list()
	fname = paths.getLogPath('stats')
	with open(fname, 'r') as h:
		content = h.read()
		for line in content.split('\n'):
			if line == '':
				continue
			data.append(Login(*json.loads(line)))
	
	# build statistics
	per_hours    = dict()
	per_country  = dict()
	per_weekdays = dict()
	for h in range(24):
		per_hours[h] = {
			'logins'  : 0,
			'ips'     : set(),
			'players' : 0
		}
	for d in range(7):
		per_weekdays[d] = {
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
		
		weekday = l.getDatetime().weekday()
		per_weekdays[weekday]['logins'] += 1
		per_weekdays[weekday]['ips'].add(l.ip)
		per_weekdays[weekday]['players'] = max(per_weekdays[weekday]['players'], l.num_players)
		  
	return per_hours, per_country, per_weekdays


def weekday2str(i):
	if i == 0:
		return 'Mon'
	elif i == 1:
		return 'Tue'
	elif i == 2:
		return 'Wed'
	elif i == 3:
		return 'Thu'
	elif i == 4:
		return 'Fri'
	elif i == 5:
		return 'Sat'
	else:
		return 'Sun'


if __name__ == '__main__':
	paths = PathApi(appname='pyvtt', root=None)
	
	analysis = paths.root / 'analysis.txt'
	
	disk_analysis = disk_report(paths)
	per_hours, per_country, per_weekdays = stats_report(paths)
	
	# create disk report
	with open(analysis, 'w') as h:
		h.write(print_disk(disk_analysis))
		h.write('\n\n')
		h.write(print_stats('Logins per Hour (UTC)', per_hours, 'logins', lambda k: k, lambda k: k))
		h.write('\n\n')
		h.write(print_stats('IPs per Hour (UTC)', per_hours, 'ips', lambda k: len(k), lambda k: k))
		h.write('\n\n')
		h.write(print_stats('Players per Hour (UTC)', per_hours, 'players', lambda k: k, lambda k: k))
		h.write('\n\n')
		h.write(print_stats('Logins per Weekday (UTC)', per_weekdays, 'logins', lambda k: k, weekday2str))
		h.write('\n\n')
		h.write(print_stats('IPs per Weekday (UTC)', per_weekdays, 'ips', lambda k: len(k), weekday2str))
		h.write('\n\n')
		h.write(print_stats('Players per Weekday (UTC)', per_weekdays, 'players', lambda k: k, weekday2str))
		h.write('\n\n')
		h.write(print_stats('Logins per Country', per_country, 'logins', lambda k: k, lambda k: k))
		h.write('\n\n')
		h.write(print_stats('IPs per Country', per_country, 'ips', lambda k: len(k), lambda k: k))
	
	print('Analysis written to {0}'.format(analysis))


