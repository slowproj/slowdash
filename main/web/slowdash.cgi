#! /usr/bin/python3
# Created by Sanshiro Enomoto on 3 Sep 2021 #
# Updated by Sanshiro Enomoto on 12 Dec 2024 for WSGI #

import sys, os
import slowdash_wsgi

slowdash_wsgi.is_cgi = True

def start_response(status, headers):
    sys.stdout.write(f'Status: {status}\r\n')
    for key, value in headers:
        sys.stdout.write(f'{key}: {value}\r\n')
    sys.stdout.write('\r\n')
    sys.stdout.flush()

result = slowdash_wsgi.application(os.environ, start_response)
for data in result:
    sys.stdout.buffer.write(data)
sys.stdout.buffer.flush()
