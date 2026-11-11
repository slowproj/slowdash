-- The views join by cid, so a name with several channels (replace_channel())
-- returns their histories joined. unit and type are those of each row's cid.

-- All the records. value is that of any numeric type (double, integer,
-- boolean) as double, for Slowdash time series; the other types are in
-- their own columns (value_jsonb for Slowdash objects).
CREATE OR REPLACE VIEW records AS
SELECT
  c.name, r.ts,
  COALESCE(r.value, r.value_int::double precision, r.value_bool::integer::double precision) AS value,
  c.unit, c.type,
  r.value_int, r.value_text, r.value_bool, r.value_jsonb,
  r.cid, r.inserted_at
FROM raw_records r
JOIN channels c USING (cid);

-- Latest value of each name, with the columns of records.
CREATE OR REPLACE VIEW latest AS
SELECT DISTINCT ON (c.name)
  c.name, l.ts,
  COALESCE(l.value, l.value_int::double precision, l.value_bool::integer::double precision) AS value,
  c.unit, c.type,
  l.value_int, l.value_text, l.value_bool, l.value_jsonb,
  l.cid, l.inserted_at
FROM raw_latest l
JOIN channels c USING (cid)
ORDER BY c.name, l.ts DESC;

-- All the settings in one place, for reading. Each is changed where it
-- lives (see "設定" in README_ja.md).
CREATE OR REPLACE VIEW settings_overview AS
SELECT 'settings' AS scope, s.name, s.value
FROM settings,
  LATERAL (VALUES
    ('schema_version', schema_version::text),
    ('installed_at', installed_at::text),
    ('max_past', max_past::text),
    ('max_future', max_future::text)
  ) AS s(name, value)
UNION ALL
SELECT 'role ' || r.rolname, 'connection_limit', r.rolconnlimit::text
FROM pg_roles r
WHERE r.rolname IN (:'admin_role', :'writer_role', :'monitor_role', :'analyzer_role')
UNION ALL
-- role settings for this database, or for all databases
SELECT * FROM (
  SELECT DISTINCT ON (r.rolname, split_part(cfg, '=', 1))
    'role ' || r.rolname, split_part(cfg, '=', 1), substr(cfg, strpos(cfg, '=') + 1)
  FROM pg_roles r
  JOIN pg_db_role_setting d ON d.setrole = r.oid
  CROSS JOIN LATERAL unnest(d.setconfig) AS cfg
  WHERE r.rolname IN (:'admin_role', :'writer_role', :'monitor_role', :'analyzer_role')
    AND d.setdatabase IN (0, (SELECT oid FROM pg_database WHERE datname = current_database()))
  ORDER BY r.rolname, split_part(cfg, '=', 1), d.setdatabase DESC
) AS role_settings
UNION ALL
SELECT 'server', s.name, current_setting(s.name)
FROM (VALUES ('server_version'), ('max_connections'), ('max_locks_per_transaction')) AS s(name);
