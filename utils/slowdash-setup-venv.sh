#! /bin/bash

echo removing old venv
rm -rf venv

echo setting up venv
python3 -m venv venv
source venv/bin/activate

# fundamental packages
pip install uvicorn pyyaml psutil bcrypt requests 

# DB interface packages
pip install psycopg2 influxdb-client redis pymongo couchdb

# Packages that user scripts might use
pip install numpy matplotlib pillow pyserial pyvisa

