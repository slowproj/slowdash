-- Updates raw_latest from the inserted values (parallel arrays), one row per cid.
-- The values are passed in, not read back from raw_records: a query on
-- raw_records without a constant ts range would lock all its partitions.
CREATE OR REPLACE FUNCTION update_latest(
  p_cid integer[], p_ts timestamptz[], p_inserted_at timestamptz,
  p_value double precision[], p_value_int bigint[], p_value_text text[],
  p_value_bool boolean[], p_value_jsonb jsonb[]
)
RETURNS void
LANGUAGE sql SET search_path FROM CURRENT
AS $$
  INSERT INTO raw_latest AS l (cid, ts, inserted_at, value, value_int, value_text, value_bool, value_jsonb)
  SELECT DISTINCT ON (u.cid)
    u.cid, u.ts, p_inserted_at, u.value, u.value_int, u.value_text, u.value_bool, u.value_jsonb
  FROM unnest(p_cid, p_ts, p_value, p_value_int, p_value_text, p_value_bool, p_value_jsonb)
    AS u(cid, ts, value, value_int, value_text, value_bool, value_jsonb)
  ORDER BY u.cid, u.ts DESC
  ON CONFLICT (cid) DO UPDATE SET
    ts = excluded.ts, inserted_at = excluded.inserted_at,
    value = excluded.value, value_int = excluded.value_int, value_text = excluded.value_text,
    value_bool = excluded.value_bool, value_jsonb = excluded.value_jsonb
  WHERE excluded.ts > l.ts
$$;


-- Recomputes raw_latest of cid (all channels if NULL) from raw_records,
-- e.g. after loading data with update_latest => false, or after changing
-- raw_records directly. Holds the writers while running: for all channels,
-- this takes seconds (it searches every partition for a stopped channel).
-- Returns the number of channels that have data.
CREATE OR REPLACE FUNCTION rebuild_latest(cid integer DEFAULT NULL)
RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path FROM CURRENT
AS $$
#variable_conflict use_column
DECLARE
  p_cid ALIAS FOR cid;
  v_count integer;
BEGIN
  -- See replace_channel()
  LOCK TABLE ONLY raw_records IN SHARE MODE;

  DELETE FROM raw_latest WHERE p_cid IS NULL OR cid = p_cid;
  INSERT INTO raw_latest (cid, ts, inserted_at, value, value_int, value_text, value_bool, value_jsonb)
  SELECT r.*
  FROM channels c
  CROSS JOIN LATERAL (
    SELECT r.cid, r.ts, r.inserted_at, r.value, r.value_int, r.value_text, r.value_bool, r.value_jsonb
    FROM raw_records r
    WHERE r.cid = c.cid
    ORDER BY r.ts DESC
    LIMIT 1
  ) r
  WHERE p_cid IS NULL OR c.cid = p_cid;
  GET DIAGNOSTICS v_count = ROW_COUNT;
  RETURN v_count;
END;
$$;
