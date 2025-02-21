#! /bin/bash

if [ ! -d app ]; then
    echo "ERROR: bad current directory: Run this script at SlowDash base directory"
    exit
fi
    
if [ -d venv ]; then
    echo "venv already exists"
else
    echo "setting up venv"
    python3 -m venv venv
fi

source venv/bin/activate

# fundamental packages
pip install uvicorn hypercorn websockets pyyaml psutil bcrypt requests 

# DB interface packages
if command -v pg_config &> /dev/null; then
    pip install psycopg2
fi
pip install influxdb-client redis pymongo couchdb

# Packages that user scripts might use
pip install numpy matplotlib pillow pyserial pyvisa

# SlowDash package
pip install -e ./lib/slowlette
