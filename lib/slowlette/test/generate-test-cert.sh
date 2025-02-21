#! /bin/bash

openssl req -x509 -nodes -days 3 -newkey rsa:2048 -keyout key.pem -out cert.pem -subj "/CN=localhost"

