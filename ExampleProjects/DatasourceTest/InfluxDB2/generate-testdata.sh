#! /bin/bash

slowdash_dir="$(dirname $(dirname $(command -v slowdash)))"
python3 $slowdash_dir/utils/generate-testdata.py --db-url=influxdb2://sloworg:slowtoken@localhost:8086/SlowTestData
