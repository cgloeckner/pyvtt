"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2022 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import logging
import sys


__author__ = 'Christian Glöckner'
__licence__ = 'MIT'


class LoggingApi(object):

    def __init__(self, quiet, info_file, error_file, access_file, warning_file, logins_file, auth_file,
                 stdout_only=False, loglevel='INFO'):
        self.log_format = logging.Formatter('[%(asctime)s at %(module)s/%(filename)s:%(lineno)d] %(message)s')

        # setup info logger
        self.info_logger = logging.getLogger('info_log')
        self.info_logger.setLevel(loglevel)

        if not stdout_only:
            self.linkFile(self.info_logger, info_file)
        if not quiet:
            self.linkStdout(self.info_logger)

        # setup error logger
        self.error_logger = logging.getLogger('error_log')
        self.error_logger.setLevel(loglevel)

        if not stdout_only:
            self.linkFile(self.error_logger, error_file)
        elif not quiet:
            self.linkStdout(self.error_logger)

        # setup access logger
        self.access_logger = logging.getLogger('access_log')
        self.access_logger.setLevel(loglevel)

        if not stdout_only:
            self.linkFile(self.access_logger, access_file)
        if not quiet:
            self.linkStdout(self.access_logger)

        # setup warning logger
        self.warning_logger = logging.getLogger('warning_log')
        self.warning_logger.setLevel(loglevel)

        if not stdout_only:
            self.linkFile(self.warning_logger, warning_file)
        if not quiet:
            self.linkStdout(self.warning_logger)

        # setup logins logger
        self.logins_logger = logging.getLogger('logins_log')
        self.logins_logger.setLevel(loglevel)

        # @NOTE: this log is required for server analysis and cannot be disabled
        self.linkFile(self.logins_logger, logins_file, skip_format=True)

        # setup auth logger
        self.auth_logger = logging.getLogger('auth_log')
        self.auth_logger.setLevel(logging.INFO)

        if not stdout_only:
            self.linkFile(self.auth_logger, auth_file)
        if not quiet:
            self.linkStdout(self.auth_logger)

        # link logging handles
        self.info = self.info_logger.info
        self.error = self.error_logger.error
        self.access = self.access_logger.info
        self.warning = self.warning_logger.warning
        self.logins = self.logins_logger.info
        self.auth = self.auth_logger.info

        if not stdout_only:
            boot = '{0} {1} {0}'.format('=' * 15, 'STARTED')
            self.info(boot)
            self.error(boot)
            self.access(boot)
            self.warning(boot)

    def linkStdout(self, target):
        """Links the given logger to stdout."""
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(self.log_format)
        target.addHandler(handler)

    def linkFile(self, target, fname, skip_format=False):
        """Links the given logger to the provided filename."""
        handler = logging.FileHandler(fname, mode='a')
        if not skip_format:
            handler.setFormatter(self.log_format)
        target.addHandler(handler)

