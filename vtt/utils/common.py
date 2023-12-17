"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2022 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'


def add_dict_set(dictionary: dict[str, set[str]], key: str, value: str) -> None:
    """ Add the value to a set inside the dictionary, specified by the
    key. If the set does not exist yet, it will be added.
    """
    if key not in dictionary:
        dictionary[key] = set()
    dictionary[key].add(value)


def count_dict_set_len(dictionary: dict) -> None:
    """ Override each set in the dict with its length.
    """
    for key in dictionary:
        dictionary[key] = len(dictionary[key])
