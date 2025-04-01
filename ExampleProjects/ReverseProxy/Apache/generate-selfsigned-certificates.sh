#! /bin/bash

mkdir -p apache2/ssl

openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout apache2/ssl/privkey.pem -out apache2/ssl/fullchain.pem -subj "/CN=localhost"
