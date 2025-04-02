#! /bin/bash

if [ $# -ne 2 ]; then
    echo "Usage: $0 USERNAME PASSED"
    exit 1
fi

APACHE2_DIR=$(dirname "${BASH_SOURCE[0]}")
htpasswd -bc $APACHE2_DIR/htpasswd "$1" "$2"
