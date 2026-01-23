#! /bin/bash

curl -X POST http://localhost:18881/api/slowdrip/sensor_value_alert/peacheese --data '{"value_raw":200, "value_cal":10}'
