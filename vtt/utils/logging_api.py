"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

import logging
import sys
import pathlib


class LoggingApi:

    def __init__(self, quiet: bool, info_file: pathlib.Path, error_file: pathlib.Path, access_file: pathlib.Path,
                 warning_file: pathlib.Path, logins_file: pathlib.Path, auth_file: pathlib.Path,
                 stdout_only: bool = False, loglevel: str = 'INFO') -> None:
        self.log_format = logging.Formatter('[%(asctime)s at %(module)s/%(filename)s:%(lineno)d] %(message)s')

        # setup info logger
        self.info_logger = logging.getLogger('info_log')
        self.info_logger.setLevel(loglevel)

        if not stdout_only:
            self.link_file(self.info_logger, info_file)
        if not quiet:
            self.link_stdout(self.info_logger)

        # setup error logger
        self.error_logger = logging.getLogger('error_log')
        self.error_logger.setLevel(loglevel)

        if not stdout_only:
            self.link_file(self.error_logger, error_file)
        elif not quiet:
            self.link_stdout(self.error_logger)

        # setup access logger
        self.access_logger = logging.getLogger('access_log')
        self.access_logger.setLevel(loglevel)

        if not stdout_only:
            self.link_file(self.access_logger, access_file)
        if not quiet:
            self.link_stdout(self.access_logger)

        # setup warning logger
        self.warning_logger = logging.getLogger('warning_log')
        self.warning_logger.setLevel(loglevel)

        if not stdout_only:
            self.link_file(self.warning_logger, warning_file)
        if not quiet:
            self.link_stdout(self.warning_logger)

        # setup logins logger
        self.logins_logger = logging.getLogger('logins_log')
        self.logins_logger.setLevel(loglevel)

        # @NOTE: this log is required for server analysis and cannot be disabled
        self.link_file(self.logins_logger, logins_file, skip_format=True)

        # setup auth logger
        self.auth_logger = logging.getLogger('auth_log')
        self.auth_logger.setLevel(logging.INFO)

        if not stdout_only:
            self.link_file(self.auth_logger, auth_file)
        if not quiet:
            self.link_stdout(self.auth_logger)

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

    def link_stdout(self, target: logging.Logger) -> None:
        """Links the given logger to stdout."""
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(self.log_format)
        target.addHandler(handler)

    def link_file(self, target: logging.Logger, path: pathlib.Path, skip_format: bool = False) -> None:
        """Links the given logger to the provided filename."""
        handler = logging.FileHandler(path, mode='a')
        if not skip_format:
            handler.setFormatter(self.log_format)
        target.addHandler(handler)
