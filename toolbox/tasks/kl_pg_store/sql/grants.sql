REVOKE ALL ON SCHEMA :"schema" FROM PUBLIC;
REVOKE ALL ON SCHEMA :"work_schema" FROM PUBLIC;
REVOKE EXECUTE ON ALL FUNCTIONS IN SCHEMA :"schema" FROM PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA :"schema" REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;

GRANT USAGE ON SCHEMA :"schema" TO :"writer_role", :"monitor_role", :"analyzer_role";
GRANT SELECT ON ALL TABLES IN SCHEMA :"schema" TO :"writer_role", :"monitor_role", :"analyzer_role";

GRANT EXECUTE ON FUNCTION
  insert_records(jsonb, boolean),
  insert_record(text, timestamptz, double precision),
  create_channel(text, text, text, text),
  ensure_partitions(integer)
TO :"writer_role";

-- Only unit and description; for the Slowdash console and scripts
GRANT EXECUTE ON FUNCTION
  describe_channel(integer, text, text),
  describe_channel(text, text, text)
TO :"writer_role", :"monitor_role";

GRANT USAGE, CREATE ON SCHEMA :"work_schema" TO :"analyzer_role";
