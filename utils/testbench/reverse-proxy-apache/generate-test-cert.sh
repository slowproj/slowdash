#! /bin/bash

openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout ./ssl/slowserver.key -out ./ssl/slowserver.crt -config ssl/slowserver-selfsigned.cnf
