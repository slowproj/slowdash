#!/bin/bash
# Run by the postgres image only when the database is created.
# The roles have no password: set them with \password (see Quick start in ../README_ja.md).
set -e
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /kl_style_store/sql/install.sql
