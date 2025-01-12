#! /usr/bin/python3

from test_slowapi import app

import slowapi_server
slowapi_server.run(app, port=18881, api_path='api', webfile_dir='.', index_file=None)
