#! /bin/bash

CERTS_DIR=$(dirname "${BASH_SOURCE[0]}")/ssl

mkdir -p "$CERTS_DIR"

openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout $CERTS_DIR/privkey.pem -out $CERTS_DIR/fullchain.pem -subj "/CN=localhost"
