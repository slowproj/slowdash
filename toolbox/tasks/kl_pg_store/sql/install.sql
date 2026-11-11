-- kl_pg_store installer. Run as a superuser:
--   psql -d kldb -v schema=kl_store -v role_prefix=kl -f sql/install.sql
-- It installs into the connected database. All the variables are optional
-- (see README_ja.md). Running this again is safe.

\set ON_ERROR_STOP on

\if :{?schema}
\else
  \set schema kl_store
\endif
\if :{?role_prefix}
\else
  \set role_prefix kl
\endif
-- applied only when the monitor role is created
\if :{?monitor_timeout}
\else
  \set monitor_timeout 30s
\endif
\if :{?monitor_connection_limit}
\else
  \set monitor_connection_limit 20
\endif

\set work_schema :schema _work
\set admin_role :role_prefix _admin
\set writer_role :role_prefix _writer
\set monitor_role :role_prefix _monitor
\set analyzer_role :role_prefix _analyzer

BEGIN;
SET LOCAL client_min_messages = warning;   -- "already exists, skipping" on reinstall

\ir roles.sql

CREATE SCHEMA IF NOT EXISTS :"schema" AUTHORIZATION :"admin_role";
CREATE SCHEMA IF NOT EXISTS :"work_schema" AUTHORIZATION :"admin_role";

-- Everything below is owned by the admin role. Functions capture this
-- search_path with "SET search_path FROM CURRENT", so that the schema name
-- does not appear in the function bodies.
SET LOCAL ROLE :"admin_role";
SET LOCAL search_path = :"schema", pg_temp;

\ir tables.sql
\ir partition.sql
\ir value.sql
\ir latest.sql
\ir channel.sql
\ir insert.sql
\ir integrity.sql
\ir views.sql
\ir grants.sql

COMMIT;
