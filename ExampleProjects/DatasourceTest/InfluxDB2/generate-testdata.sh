#! /bin/bash

python3 $SLOWDASH_DIR/utils/generate-testdata.py --db-url=influxdb2://sloworg:slowtoken@localhost:8086/SlowTestData
