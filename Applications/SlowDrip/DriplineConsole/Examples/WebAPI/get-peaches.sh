#! /bin/bash

URL="http://localhost:18881/api/slowdrip/endpoint/peaches"

value=$(curl -s "$URL")
echo ${value}
