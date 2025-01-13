#! /usr/bin/python3

# temporary until SlowAPI becomes a package
import sys, os
sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir))

import slowapi
from test_slowapi import app

slowapi.run(app, port=18881, api_path='api', webfile_dir='.', index_file=None)
