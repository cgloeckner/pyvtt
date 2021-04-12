#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import time, datetime, os, json
import xlsxwriter

import orm

from utils import PathApi


__author__ = 'Christian Glöckner'
__licence__ = 'MIT'


# ---------------------------------------------------------------------

def fetchGameDiskUsage(paths, gm_url, game_url):
    """ Fetch data about a game's disk usage.
    Returns all images and the game's size in bytes.
    """
    # query all images
    p = paths.getGamePath(gm_url, game_url)
    all_images = os.listdir(p)
    
    # query total size
    size = 0
    for fname in all_images:
        size += os.path.getsize(p / fname)

    return {'game_url': game_url, 'num_files': len(all_images), 'size': size}

def fetchGmDiskUsage(paths, gm_url):
    """ Fetch data about a GM's disk usage.
    Returns tuple with number of files, total games' size and total
    number of games.
    """
    num_files = 1 # gm.db
    size      = os.path.getsize(paths.getDatabasePath(gm_url))
    num_games = 0
    
    # query all games
    games = list()
    p = paths.getGmsPath(gm_url)
    for game_url in os.listdir(p):
        if os.path.isdir(p / game_url):
            r = fetchGameDiskUsage(paths, gm_url, game_url)
            num_files += r['num_files']
            size      += r['size']
            num_games += 1

    return {'gm_url': gm_url, 'num_files': num_files, 'size': size, 'num_games': num_games}

def fetchGameTimeids(paths, gm_url, engine):
    """ Fetch GM's games' time-IDs.
    """
    # load GM's database
    db_path = str(paths.getDatabasePath(gm_url))
    db = orm.createGmDatabase(engine, db_path)

    # iterate all games
    data = dict()
    with orm.db_session:
        for game in db.Game.select():
            data[game.url] = game.timeid
    
    return data

def fetchAllGameTimeids(paths):
    """ Fetch all game's time-IDs.
    """
    # load GMs database
    class DummyEngine(object):
        def __init__(self, p):
            self.paths = p
            settings_path = self.paths.getSettingsPath()
            with open(settings_path, 'r') as h:
                settings = json.load(h)
            self.expire = settings['expire']
            
    engine = DummyEngine(paths)
    main_db = orm.createMainDatabase(engine)

    # fetch all all GMs
    # NOTE: cannot nest db_sessions inside each other
    data = dict()
    with orm.db_session:
        gms = [gm.url for gm in main_db.GM.select()]
    for gm_url in gms:
        data[gm_url] = fetchGameTimeids(paths, gm_url, engine)

    # group games by timeids
    grouped = {
        5     : list(),
        10    : list(),
        15    : list(),
        30    : list(),
        60    : list(), # 1h
        120   : list(), # 2h
        720   : list(), # 12h
        1440  : list(), # 1d
        10080 : list(), # 1w
    }
    outdated = list()
    now = time.time()
    
    for gm_url in data:
        for game_url in data[gm_url]:
            key    = '{0}/{1}'.format(gm_url, game_url)
            timeid = data[gm_url][game_url]
            delta  = (now - timeid) / 60 # in minutes
            for threshold in grouped:
                if delta < threshold:
                    grouped[threshold].append(key)
                    break
            if delta > engine.expire * 60:
                outdated.append(key)
    
    return (grouped, outdated)

def fetchTotalDiskUsage(paths):
    """ Fetch data about disk usage.
    Returns tuple with number of games, number of files, all
    GMs' disk usage in bytes and a list of GMs.
    """
    num_games = 0
    num_files = 0
    size      = 0   
    gms       = list()

    # fetch all GMs
    p = paths.getGmsPath()
    for gm_url in os.listdir(p):
        r = fetchGmDiskUsage(paths, gm_url)
        num_files += r['num_files']
        size      += r['size']
        num_games += r['num_games']
        gms.append(r)

    # sort GMs by size (descending)
    gms.sort(key=lambda record: record['size'], reverse=True)

    return {'num_games': num_games, 'num_files': num_files, 'size': size, 'gms': gms}


# ---------------------------------------------------------------------

class LoginRecord(object):
    
    def __init__(self, is_gm, timeid, country, ip, num_players):
        self.is_gm       = is_gm
        self.timeid      = timeid
        self.country     = country
        self.ip          = ip
        self.num_players = num_players

def parseLoginFile(paths):
    records = list()
    with open(paths.getLogPath('stats'), 'r') as h:
        content = h.read()
        for line in content.split('\n'):
            if line == '':
                continue
            args = json.loads(line)
            records.append(LoginRecord(*args))
    return records

def fetchIpsByCountry(logins):
    data  = dict()
    now   = time.time()
    since = now - 30 * 24 * 3600 # past 30d

    # group IPs by country
    for record in logins:
        if record.timeid < since:
            continue
        if record.country not in data:
            data[record.country] = set()
        data[record.country].add(record.ip)

    # count IPs per country
    for key in data:
        data[key] = len(data[key])

    return data

def formatWeekday(dt):
    i = dt.weekday()
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

def twodigit(h):
    if h < 10:
        return '0{0}'.format(h)
    else:
        return str(h)

def formatDate(dt):
    return '{0}/{1}/{2}'.format(str(dt.year)[2:], twodigit(dt.month), twodigit(dt.day))

def formatHour(h):
    if h < 12:
        return '{0} am'.format(twodigit(h))
    else:
        return '{0} pm'.format(twodigit(h-12))

def fetchIpsByWeek(logins):
    data  = dict()

    formatter = lambda dt: '{0}/{1}'.format(str(dt.year)[2:], dt.isocalendar()[1])

    # group IPs by week 
    for record in logins:
        dt = datetime.datetime.fromtimestamp(record.timeid)
        key = formatter(dt)
        if key not in data:
            data[key] = set()
        data[key].add(record.ip)

    # count IPs per week
    for key in data:
        data[key] = len(data[key])
    
    return data

def fetchPlayersByHour(logins):
    data  = dict()
    now   = time.time()
    since = now - 14 * 24 * 3600 # past 14d

    formatter = lambda dt: '{0} {1}'.format(formatDate(dt), formatWeekday(dt))
    
    # pre-populate dict
    delta = datetime.timedelta(days=1)
    dt    = datetime.datetime.fromtimestamp(since)
    now   = datetime.datetime.fromtimestamp(now)
    while dt <= now:
        date_str = formatter(dt)
        data[date_str] = dict()
        for hr in range(24):
            data[date_str][hr] = set()
        dt += delta

    # group number of players by hour
    for record in logins:
        if record.timeid < since:
            continue
        dt = datetime.datetime.fromtimestamp(record.timeid)
        date_str = formatter(dt)
        data[date_str][dt.hour].add(record.num_players)

    # count maximum number of players per hour 
    for date_str in data:
        for hour in data[date_str]:
            tmp = data[date_str][hour]
            data[date_str][hour] = max(tmp) if len(tmp) > 0 else 0

    return data


# ---------------------------------------------------------------------

def printGameTimeids(doc, timeids):
    grouped  = timeids[0]
    outdated = timeids[1]

    # prepare new worksheet
    sheet = doc.add_worksheet('Timeid Report')
    
    align = doc.add_format({'align': 'center'})
    title = doc.add_format({'align': 'center', 'bold' : True})
    
    # header
    for col, caption in enumerate(['<5min', '<10min', '<15min', '<30min', '<1h', '<2h', '<12h', '<1d', '<1w', 'outdated']):
        sheet.write(0, col, caption, title)
    sheet.set_column(0, len(grouped), 10, align)

    for i, threshold in enumerate(grouped):
        row = 1
        sheet.write(row, i, len(grouped[threshold]))
        """
        for url in grouped[threshold]:
            sheet.write(row, i, url)
            row += 1
        row += 1
        """
    
    row = 1
    for url in outdated:
        sheet.write(row, i+1, url)

def formatBytes(b):
    if b > 1024 * 1024:
        return '{0} MiB  '.format(int(b / (1024*1024)))
    else:
        return '< 1 MiB'

def printDiskUsage(doc, data):
    # prepare new worksheet
    sheet = doc.add_worksheet('Disk Report')
    
    align = doc.add_format({'align': 'center'})
    title = doc.add_format({'align': 'center', 'bold' : True})

    # header
    for col, caption in enumerate(['GM ID', 'Games', 'Files', 'Space']):
        sheet.write(0, col, caption, title)
    sheet.set_column(0, 0, 15, align)
    sheet.set_column(1, 3, 10, align)

    # write report data
    row = 1
    for gm in data['gms']:
        sheet.write(row, 0, gm['gm_url'])
        sheet.write(row, 1, gm['num_games'])
        sheet.write(row, 2, gm['num_files'])
        sheet.write(row, 3, formatBytes(gm['size']))
        row += 1

    # footer
    sheet.write(row+1, 0, '{0} GMs'.format(len(data['gms'])), title)
    sheet.write(row+1, 1, '{0} Games'.format(data['num_games']), title)
    sheet.write(row+1, 2, '{0} Files'.format(data['num_files']), title)
    sheet.write(row+1, 3, formatBytes(data['size']), title)

def printIpsByCountry(doc, data):
    # prepare new worksheet
    sheet = doc.add_worksheet('Country Report (30d)')
    
    align = doc.add_format({'align': 'center'})
    title = doc.add_format({'align': 'center', 'bold' : True}) 
    perc  = doc.add_format({'align': 'center', 'num_format': '0.00" "%'})

    # header
    for col, caption in enumerate(['Country', 'Users', '%']):
        sheet.write(0, col, caption, title)
    sheet.set_column(0, 1, 15, align)
    sheet.set_column(2, 2, 15, perc)

    # write report data
    total = 0
    for country in data:
        total += data[country]
    row = 1
    for country in data:
        sheet.write(row, 0, country)
        sheet.write(row, 1, data[country])
        sheet.write(row, 2, data[country] / total)
        row += 1

def printIpsByWeek(doc, data):
    # prepare new worksheet
    sheet = doc.add_worksheet('Past Weeks Report')
    
    align = doc.add_format({'align': 'center'})
    title = doc.add_format({'align': 'center', 'bold' : True}) 

    # header
    for col, caption in enumerate(['Week', 'Users']):
        sheet.write(0, col, caption, title)
    sheet.set_column(0, 0, 15, align)
    sheet.set_column(1, 1, 8, align)

    # write report data
    row = 1
    for week in data:
        sheet.write(row, 0, week)
        sheet.write(row, 1, data[week])
        row += 1

def printPlayersByHour(doc, data):
    # prepare new worksheet
    sheet = doc.add_worksheet('Last Days Report')
    
    align   = doc.add_format({'align': 'center'})
    title   = doc.add_format({'align': 'center', 'bold' : True})
    rotated = doc.add_format({'align': 'center', 'rotation': 90}) 

    # header
    sheet.write(1, 0, 'Date', title)
    for col, day in enumerate(data):
        sheet.write(0, col+1, day.split(' ')[0], rotated)
        sheet.write(1, col+1, day.split(' ')[1], title)

    sheet.set_row(0, 50)
    sheet.set_column(0, 0, 15, align)
    sheet.set_column(1, col+1, 5, align)

    # write report data
    for col, day in enumerate(data):
        row = 2
        for hour in range(24):
            sheet.write(row, 0, formatHour(hour))
            sheet.write(row, col+1, data[day][hour])
            row += 1


# ---------------------------------------------------------------------


if __name__ == '__main__':
    paths = PathApi(appname='pyvtt', root=None)
    fname = paths.root / 'analysis.xlsx'
    
    timeids = fetchAllGameTimeids(paths)
    disk = fetchTotalDiskUsage(paths)
    logins    = parseLoginFile(paths)
    byCountry = fetchIpsByCountry(logins)
    byWeek    = fetchIpsByWeek(logins)
    byHour    = fetchPlayersByHour(logins)
    
    doc   = xlsxwriter.Workbook(fname)
    printGameTimeids(doc, timeids)
    printDiskUsage(doc, disk)
    printIpsByCountry(doc, byCountry)
    printIpsByWeek(doc, byWeek)
    printPlayersByHour(doc, byHour)
    doc.close()

