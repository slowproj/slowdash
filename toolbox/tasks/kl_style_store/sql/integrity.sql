-- Checks the invariants that the functions keep, e.g. after changing the
-- tables by direct SQL. Returns one row per problem; empty if consistent.
-- The checks on the values scan raw_records in [ts_from, ts_to): for all
-- time, this reads the whole table. The other checks use the index only.
CREATE OR REPLACE FUNCTION check_integrity(ts_from timestamptz DEFAULT '-infinity', ts_to timestamptz DEFAULT 'infinity')
RETURNS TABLE (problem text, cid integer, detail text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path FROM CURRENT
AS $$
#variable_conflict use_column
DECLARE
  p_from ALIAS FOR ts_from;
  p_to ALIAS FOR ts_to;
BEGIN
  -- records of an unknown cid, or in the wrong value column for the type
  RETURN QUERY
  SELECT
    CASE WHEN c.cid IS NULL THEN 'unknown_cid' ELSE 'wrong_value_column' END,
    r.cid,
    format('%s records from %s to %s', count(*), min(r.ts), max(r.ts))
  FROM raw_records r
  LEFT JOIN channels c ON c.cid = r.cid
  WHERE r.ts >= p_from AND r.ts < p_to
    AND (c.cid IS NULL OR CASE c.type
      WHEN 'double' THEN r.value IS NULL
      WHEN 'integer' THEN r.value_int IS NULL
      WHEN 'boolean' THEN r.value_bool IS NULL
      WHEN 'text' THEN r.value_text IS NULL
      WHEN 'json' THEN r.value_jsonb IS NULL
    END)
  GROUP BY r.cid, c.cid;

  -- records outside the validity period [valid_from, next valid_from)
  RETURN QUERY
  SELECT 'out_of_validity', p.cid, format('records outside [%s, %s)', p.valid_from, p.valid_to)
  FROM (
    SELECT c.cid, c.valid_from, lead(c.valid_from, 1, 'infinity') OVER (PARTITION BY c.name ORDER BY c.valid_from) AS valid_to
    FROM channels c
  ) p
  WHERE EXISTS (SELECT 1 FROM raw_records r WHERE r.cid = p.cid AND r.ts < p.valid_from)
     OR EXISTS (SELECT 1 FROM raw_records r WHERE r.cid = p.cid AND r.ts >= p.valid_to);

  -- raw_latest differs from the latest record (fix: rebuild_latest(cid))
  RETURN QUERY
  SELECT 'latest_mismatch', COALESCE(l.cid, r.cid),
    format('raw_latest: %s, raw_records: %s', l.ts, r.ts)
  FROM channels c
  LEFT JOIN LATERAL (
    SELECT r.cid, r.ts, r.value, r.value_int, r.value_text, r.value_bool, r.value_jsonb
    FROM raw_records r WHERE r.cid = c.cid ORDER BY r.ts DESC LIMIT 1
  ) r ON true
  FULL JOIN raw_latest l ON l.cid = c.cid
  WHERE (r.cid IS NOT NULL OR l.cid IS NOT NULL)
    AND (l.cid IS NULL OR r.cid IS NULL
      OR (l.ts, l.value, l.value_int, l.value_text, l.value_bool, l.value_jsonb)
         IS DISTINCT FROM (r.ts, r.value, r.value_int, r.value_text, r.value_bool, r.value_jsonb));
END;
$$;
