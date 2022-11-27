#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import sys, requests, json


__author__ = 'Christian Glöckner'
__licence__ = 'MIT'


def main():
    if len(sys.argv) < 3:
        print(f'Usage:\t{sys.argv[0]} <server_domain> <filename>')
        print('')
        print('Details:')
        print('\t<server_domain> like https://icvtt.net')
        print('\t<filename>      like /tmp/out.json')
        print('')
        return
    
    domain = sys.argv[1]
    fname  = sys.argv[2]

    data = dict()
    data['build']  = requests.get(f'{domain}/vtt/api/build', timeout=3).json()
    data['users']  = requests.get(f'{domain}/vtt/api/users', timeout=3).json()
    data['logins'] = requests.get(f'{domain}/vtt/api/logins', timeout=3).json()
    data['auth0']  = requests.get(f'{domain}/vtt/api/auth0', timeout=3).json()

    with open(fname, 'w') as h:
        json.dump(data, h, indent=4)


if __name__ == '__main__':
    main()

