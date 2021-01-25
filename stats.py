#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import time, datetime, os, json
import xlsxwriter

from utils import PathApi


__author__ = 'Christian Glöckner'
__licence__ = 'MIT'


def formatBytes(b):
    if b > 1024 * 1024:
        return '{0} MiB  '.format(int(b / (1024*1024)))
    else:
        return '< 1 MiB'

def getHour(stamp):
    """Hour"""
    return datetime.datetime.fromtimestamp(stamp).hour

def getWeekday(stamp):
    """Weekday"""
    return datetime.datetime.fromtimestamp(stamp).weekday()

def formatHour(h):
    if h < 12:
        return '{0}-{1} am'.format(h, h+1)
    else:
        return '{0}-{1} pm'.format(h-12, h-11)

def formatWeekday(i):
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


# ---------------------------------------------------------------------

class GameDiskReport(object):
    
    def __init__(self, paths, gm_url, game_url):
        self.url = game_url
        
        # query all images
        p = paths.getGamePath(gm_url, game_url)
        self.all_images = os.listdir(p)
        
        # query total size
        self.size = 0
        for fname in self.all_images:
            self.size += os.path.getsize(p / fname)


class GmDiskReport(object):
    
    def __init__(self, paths, gm_url):
        self.url       = gm_url    
        self.num_files = 1 # gm.db
        self.size      = os.path.getsize(paths.getDatabasePath(gm_url))
        
        # query all games
        self.games = list()
        p = paths.getGmsPath(gm_url)
        for game_url in os.listdir(p):
            if os.path.isdir(p / game_url):
                r = GameDiskReport(paths, gm_url, game_url)
                self.num_files += len(r.all_images)
                self.size      += r.size
                self.games.append(r)
        
    def __call__(self, row, sheet):
        sheet.write(row, 0, self.url)
        sheet.write(row, 1, len(self.games))
        sheet.write(row, 2, self.num_files)
        sheet.write(row, 3, formatBytes(self.size))


class FullDiskReport(object):
    
    def __init__(self, paths):
        # query all GMs
        self.gms       = list()
        self.num_games = 0
        self.num_files = 0
        self.size      = 0
        p = paths.getGmsPath()
        for gm_url in os.listdir(p):
            r = GmDiskReport(paths, gm_url)
            self.num_games += len(r.games)
            self.num_files += r.num_files
            self.size      += r.size
            self.gms.append(r)
        
    def __call__(self, doc):
        align = doc.add_format({'align': 'center'})
        title = doc.add_format({'align': 'center', 'bold' : True})
        
        # prepare new worksheet
        sheet = doc.add_worksheet('Disk Report')
        sheet.set_column(0, 0, 20, align)
        sheet.set_column(1, 3, 15, align)
        
        # header
        for col, caption in enumerate(['GM ID', 'Games', 'Files', 'Space']):
            sheet.write(0, col, caption, title)
        
        # write report data
        row = 1
        for gm_report in self.gms:
            gm_report(row, sheet)
            row += 1
        
        # footer
        sheet.write(row+1, 0, '{0} GMs'.format(len(self.gms)), title)
        sheet.write(row+1, 1, '{0} Games'.format(self.num_games), title)
        sheet.write(row+1, 2, '{0} Files'.format(self.num_files), title)
        sheet.write(row+1, 3, formatBytes(self.size), title)


class StatsReport(object):
    
    def __init__(self):
        self.paths = PathApi(appname='pyvtt', root=None)
        self.fname = self.paths.root / 'analysis.xlsx'
        self.doc   = xlsxwriter.Workbook(self.fname)
        
        self.full_disk_report  = FullDiskReport(self.paths)
        self.full_login_report = FullLoginReport(self.paths)
        
        self.full_disk_report(self.doc)
        self.full_login_report(self.doc)
        
        self.doc.close()


class LoginRecord(object):
    
    def __init__(self, is_gm, timeid, country, ip, num_players):
        self.is_gm       = is_gm
        self.timeid      = timeid
        self.country     = country
        self.ip          = ip
        self.num_players = num_players


class CountryLoginReport(object):
    
    def __init__(self, country):
        self.country     = country
        self.num_logins  = 0
        self.ips         = set()
        
    def update(self, record):
        self.num_logins += 1
        self.ips.add(record.ip)
        
    def __call__(self, row, sheet, total_logins, total_ips):
        sheet.write(row, 0, self.country)
        sheet.write(row, 1, self.num_logins)
        sheet.write(row, 2, len(self.ips))   
        sheet.write(row, 3, self.num_logins / total_logins)
        sheet.write(row, 4, len(self.ips) / total_ips)


class PerCountryLoginReport(object):
    
    def __init__(self, records, since=0):
        self.reports     = dict()
        self.num_logins  = 0
        self.ips         = set()
        for r in records:
            if r.timeid >= since:
                self.num_logins += 1
                self.ips.add(r.ip)
                # create new report
                if r.country not in self.reports:
                    self.reports[r.country] = CountryLoginReport(r.country)
                # update with record
                self.reports[r.country].update(r)
        
    def __call__(self, doc):
        align = doc.add_format({'align': 'center'})
        title = doc.add_format({'align': 'center', 'bold' : True})
        perc  = doc.add_format({'align': 'center', 'num_format': '0.00" "%'})
        
        # prepare new worksheet
        sheet = doc.add_worksheet('Logins by Country')
        sheet.set_column(0, 2, 15, align)
        sheet.set_column(3, 4, 10, perc)
        
        for col, caption in enumerate(['Country', 'Logins', 'IPs', 'Logins (%)', 'IPs (%)']):
            sheet.write(0, col, caption, title)
        
        # write report data
        row = 1
        for country in self.reports:
            self.reports[country](row, sheet, self.num_logins, len(self.ips))
            row += 1
        
        # footer
        sheet.write(row+1, 0, '{0} Countries'.format(len(self.reports)), title)
        sheet.write(row+1, 1, '{0} Logins'.format(self.num_logins), title)
        sheet.write(row+1, 2, '{0} IPs'.format(len(self.ips)), title)


class TimestampLoginReport(object):
    
    def __init__(self, label):
        self.label       = label
        self.num_logins  = 0
        self.num_players = 0
        self.ips         = set()
        
    def update(self, record):
        self.num_logins += 1
        self.num_players = max(self.num_players, record.num_players)
        self.ips.add(record.ip)
        
    def __call__(self, row, sheet, total_logins, total_ips):
        sheet.write(row, 0, self.label)
        sheet.write(row, 1, self.num_players)
        sheet.write(row, 2, self.num_logins)
        sheet.write(row, 3, len(self.ips))                 
        sheet.write(row, 4, self.num_logins / total_logins)
        sheet.write(row, 5, len(self.ips) / total_ips)
        

class PerTimestampLoginReport(object):
    
    def __init__(self, records, extract_func, print_func, since=0):
        self.extract_func = extract_func # extract e.g. hour from timestamp
        self.print_func   = print_func   # match e.g. 0 to Monday
        self.reports      = dict()
        self.num_logins   = 0
        self.ips          = set()
        for r in records:   
            if r.timeid >= since:
                self.num_logins += 1
                self.ips.add(r.ip)
                time_point = extract_func(r.timeid)
                # create new report
                if time_point not in self.reports:
                    self.reports[time_point] = TimestampLoginReport(print_func(time_point))
                # update with record
                self.reports[time_point].update(r)
        
    def __call__(self, doc, add_label=None):
        align = doc.add_format({'align': 'center'})
        title = doc.add_format({'align': 'center', 'bold' : True})
        perc  = doc.add_format({'align': 'center', 'num_format': '0.00" "%'})
        
        # prepare new worksheet
        label = 'Logins by {0}'.format(self.extract_func.__doc__)
        if add_label is not None:
            label += add_label
        sheet = doc.add_worksheet(label)
        sheet.set_column(0, 3, 15, align)
        sheet.set_column(4, 5, 10, perc)
        
        for col, caption in enumerate([self.extract_func.__doc__, 'Active Players', 'Logins', 'IPs', 'Logins (%)', 'IPs (%)']):
            sheet.write(0, col, caption, title)
        
        # write report data
        max_row = 1
        for time_point in self.reports:
            current_row = time_point + 1
            self.reports[time_point](current_row, sheet, self.num_logins, len(self.ips))
            max_row = max(max_row, current_row)
        
        # footer                     
        sheet.write(max_row+2, 2, '{0} Logins'.format(self.num_logins), title)
        sheet.write(max_row+2, 3, '{0} IPs'.format(len(self.ips)), title)


class FullLoginReport(object):
    
    def __init__(self, paths):
        # parse stats from dedicated logfile
        self.records = list()
        with open(paths.getLogPath('stats'), 'r') as h:
            content = h.read()
            for line in content.split('\n'):
                if line == '':
                    continue
                args = json.loads(line)
                self.records.append(LoginRecord(*args))
        
        # build statistics
        self.per_country = PerCountryLoginReport(self.records)
        self.per_hour    = PerTimestampLoginReport(self.records, getHour, formatHour)
        self.per_weekday = PerTimestampLoginReport(self.records, getWeekday, formatWeekday)
        
        since = time.time() - 3600*24*7*4 # last 4 weeks
        self.per_hour_month    = PerTimestampLoginReport(self.records, getHour, formatHour, since=since)
        self.per_weekday_month = PerTimestampLoginReport(self.records, getWeekday, formatWeekday, since=since)
        
        since = time.time() - 3600*24
        self.yesterday = PerTimestampLoginReport(self.records, getHour, formatHour, since=since)
        
    def __call__(self, doc):
        self.per_country(doc)
        self.per_hour(doc)
        self.per_weekday(doc)
        self.per_hour_month(doc, ' (4 weeks)')
        self.per_weekday_month(doc, ' (4 weeks)')
        self.yesterday(doc, ' (24 hours)')


if __name__ == '__main__':
    StatsReport()

