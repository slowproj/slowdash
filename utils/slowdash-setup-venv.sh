#! /bin/bash

echo removing old venv
rm -rf venv

echo setting up venv
python3 -m venv venv
source venv/bin/activate

# fundamental packages
pip install uvicorn websockets pyyaml psutil bcrypt requests 

# DB interface packages
if command -v pg_config &> /dev/null; then
    pip install psycopg2
fi
pip install influxdb-client redis pymongo couchdb

# Packages that user scripts might use
pip install numpy matplotlib pillow pyserial pyvisa

