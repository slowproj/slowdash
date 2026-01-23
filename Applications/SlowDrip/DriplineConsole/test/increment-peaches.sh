#! /bin/bash

URL="http://localhost:18881/api/slowdrip/endpoint/peaches"

value_raw=$(curl -s "$URL" | jq '.value_raw')
new_value=$((value_raw + 1))
echo "${value_raw} --> ${new_value}"

curl -X POST "$URL" --data "$new_value"
echo
