#! /usr/bin/env python3

import sys, json
from argparse import ArgumentParser

try:
    import bcrypt
except:
    print('install python module "bcrypt"')
    sys.exit(-1)


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument(
        'USER', nargs=1,
        help='user name'
    )
    parser.add_argument(
        'PASS', nargs=1,
        help='password'
    )

    args = parser.parse_args()
    name, word = args.USER[0], args.PASS[0]
    key = bcrypt.hashpw(word.encode(), bcrypt.gensalt(rounds=12, prefix=b"2a")).decode()

    doc = { 'authentication': { "type": "Basic", "key": "%s:%s" % (name, key) } }
    print(json.dumps(doc, indent=4))
