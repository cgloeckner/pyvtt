"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2022 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'


import dataclasses
import argparse
import os
import typing

from dotenv import load_dotenv


def flag_settings() -> dict[str, str | int | bool]:
    parser = argparse.ArgumentParser(
        description="Startup flags for ICVTT"
    )
    parser.add_argument(
        "--appname", "--app-name", "--app_name", dest="app_name", type=str,
        help="Application name used in html title and preference " \
        "directory name"
    )
    parser.add_argument(
        "--prefdir", "--pref-dir", "--pref_dir",
        dest="pref_dir", type=str,
        help="Root path for preference directory. Defaults to " \
        "~/.local/share"
    )
    parser.add_argument(
        "--loglevel", "--log-level", "--log_level",
        dest="log_level", type=str, help="Logging level"
    )
    parser.add_argument(
        "--singledbmode", "--single-db-mode", "--single_db_mode",
        dest="single_db_mode", action="store_true",
        help="Force to use a single SQLite database file instead " \
        "of multiple files"
    )
    parser.add_argument(
        "--localhost", action="store_true",
        help="Restrict server to 127.0.0.1"
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Suppress notification API and enable catching all " \
        "exceptions in browser"
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Suppress logging to stdout"
    )
    parser.add_argument(
        "--nologs", "--no-logs", "--no_logs",
        dest="no_logs", action="store_true",
        help="Suppress logging to files"
    )

    args = parser.parse_args()
    return {
        key: value
        for key, value in vars(args).items()
        if value
    }


def env_settings(**kwargs) -> dict[str, typing.Any]:
    load_dotenv()

    ints = {"port", "limit_token", "limit_bg", "limit_game",
            "limit_music", "num_music", "cleanup_expire"}
    bools = {"ssl", "reverse_proxy"}

    for key, value in os.environ.items():
        if not key.startswith("VTT_"):
            # ignore
            continue

        # convert if necessary
        suffix = key.split("VTT_", 1)[-1].lower()
        if suffix is bools:
            value = value.lower() in ("true", "1", "yes", "on")
        elif suffix in ints:
            value = int(value)
        
        # update default value
        kwargs.setdefault(suffix, value)

    return kwargs
    


@dataclasses.dataclass
class Settings:
    # general arguments
    app_name: str = "icvtt"
    pref_dir: str = ""
    log_level: str = "INFO"

    # debugging flags
    single_db_mode: bool = False
    localhost: bool = False
    debug: bool = False
    quiet: bool = False
    no_logs: bool = False

    # hosting parameters
    domain: str = "localhost"
    port: int = 8080
    ssl: bool = False
    reverse_proxy: bool = False

    # file limits in megabytes
    limit_token: int = 2
    limit_bg: int = 10
    limit_game: int = 20  # zips
    limit_music: int = 10
    num_music: int = 6

    # cleanup settings
    cleanup_expire: int = 2592000  # expire after 30d
    cleanup_time: str = "03:00"  # cleanup at 3am

    webhook_discord_url: str | None = None
    webhook_user: str = ""
