"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2022 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'


def addDictSet(dictionary, key, value):
    """ Add the value to a set inside the dictionary, specified by the
    key. If the set does not exist yet, it will be added.
    """
    if key not in dictionary:
        dictionary[key] = set()
    dictionary[key].add(value)


def countDictSetLen(dictionary):
    """ Override each set in the dict with its length.
    """
    for key in dictionary:
        dictionary[key] = len(dictionary[key])

