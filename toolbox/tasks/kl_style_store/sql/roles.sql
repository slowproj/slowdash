-- Roles are shared by all databases in the cluster; this part needs a superuser.
-- Passwords are not set here: use "\password <role>" or ALTER ROLE ... PASSWORD.

SELECT NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'monitor_role') AS new_monitor_role \gset

SELECT format('CREATE ROLE %I LOGIN', r)
FROM unnest(ARRAY[:'admin_role', :'writer_role', :'monitor_role', :'analyzer_role']) AS r
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r)
\gexec

-- Defaults only; not overwritten on reinstall so that local tuning survives.
-- Role settings apply only to the role that logs in, not to its members.
\if :new_monitor_role
  ALTER ROLE :"monitor_role" CONNECTION LIMIT :monitor_connection_limit;
  ALTER ROLE :"monitor_role" IN DATABASE :"DBNAME" SET statement_timeout = :'monitor_timeout';
\endif

ALTER ROLE :"admin_role" IN DATABASE :"DBNAME" SET search_path = :"schema", public;
ALTER ROLE :"writer_role" IN DATABASE :"DBNAME" SET search_path = :"schema", public;
ALTER ROLE :"monitor_role" IN DATABASE :"DBNAME" SET search_path = :"schema", public;
ALTER ROLE :"analyzer_role" IN DATABASE :"DBNAME" SET search_path = :"work_schema", :"schema", public;

-- Shows the queries of all sessions in the cluster; for the administrator only.
GRANT pg_read_all_stats TO :"admin_role";
