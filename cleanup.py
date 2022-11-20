#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import threading, time, datetime


__author__ = 'Christian Glöckner'
__licence__ = 'MIT'


class CleanupThread(object):

    def __init__(self, engine):
        self.engine = engine
        
        self.worker = threading.Thread(target=self.run)
        self.worker.setDaemon(True)
        self.worker.start()

    def cleanup(self):
        # cleanup and measure time
        start = time.time()
        gms, games, num_zips, num_bytes, num_rolls, num_tokens, num_md5s = self.engine.cleanupAll()
        delta = time.time() - start
        
        results = {
            'gms'    : gms,
            'games'  : games,
            'zips'   : num_zips,
            'bytes'  : num_bytes,
            'rolls'  : num_rolls,
            'tokens' : num_tokens,
            'md5s'   : num_md5s,
            'time'   : delta
        }

        # notify about cleanup results
        if self.engine.notify_api is not None:
            self.engine.notify_api.onCleanup(results)

    def getNextUpdate(self):      
        h, m   = self.engine.cleanup['daytime'].split(':')
        now    = datetime.datetime.today()
        future = datetime.datetime(now.year, now.month, now.day, int(h), int(m))
        if now > future:
            future += datetime.timedelta(days=1)
        return future, (future-now)

    def run(self):
        while True:
            # cleanup engine
            self.cleanup()

            # schedule cleanup
            when, delta = self.getNextUpdate()
            time.sleep(delta.total_seconds())
