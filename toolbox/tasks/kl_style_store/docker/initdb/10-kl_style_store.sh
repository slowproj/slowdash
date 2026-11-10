#!/bin/bash
# Run by the postgres image only when the database is created.
set -e
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /kl_style_store/sql/install.sql
# an empty password: no password, i.e. only from inside the container
for role in admin writer monitor analyzer; do
    var="KL_${role^^}_PASSWORD"
    if [ -n "${!var}" ]; then
        psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v password="${!var}" \
             <<< "ALTER ROLE kl_$role PASSWORD :'password';"
    fi
done
