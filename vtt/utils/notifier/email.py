"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'


import json
import smtplib

from gevent import lock

from .common import Notifier


# FIXME: deprecated implementation


# Email API for error notification
# @NOTE: this class is not covered in the unit tests because it depends too much on external resources
class EmailApi(Notifier):

    def __init__(self, engine, **data):
        self.engine = engine
        self.appname = data['appname']
        self.host = data['host']
        self.port = data['port']
        self.sender = data['sender']
        self.user = data['user']
        self.password = data['password']
        self.lock = lock.RLock()
        self.login()

    def login(self):
        with self.lock:
            self.smtp = smtplib.SMTP(f'{self.host}:{self.port}')
            self.smtp.starttls()
            self.smtp.login(self.user, self.password)

    def send(self, subject, message):
        # create mail content
        frm = f'From: pyvtt Server <{self.sender}>'
        to = f'To: Developers <{self.sender}>'
        sub = f'Subject: [{self.appname}/{self.engine.title}] {subject}'
        plain = f'{frm}\n{to}\n{sub}\n{message}'

        # send email
        try:
            with self.lock:
                self.smtp.sendmail(self.sender, self.sender, plain)
        except smtplib.SMTPServerDisconnected:
            # re-login and re-try
            self.smtp.connect(f'{self.host}:{self.port}')
            self.login()
            self.smtp.sendmail(self.sender, self.sender, plain)
        except smtplib.SMTPSenderRefused:
            # re-login and re-try
            self.login()
            self.smtp.sendmail(self.sender, self.sender, plain)

    def on_start(self):
        msg = f'The VTT server {self.appname}/{self.engine.title} on {self.engine.getDomain()} is now online!'
        self.send('Server Online', msg)

    def on_cleanup(self, report):
        report = json.dumps(report, indent=4)
        msg = f'The VTT Server finished cleanup.\n{report}'
        self.send('Periodic Cleanup', msg)

    def on_error(self, error_id, message):
        sub = f'Exception Traceback #{error_id}'
        self.send(sub, message)
