-- Parameters of the public functions have plain names, for the named
-- notation (update_latest => false); as they clash with column names, the
-- bodies use the p_ aliases. The internal functions use p_ names directly.

-- The entry point for writing. records is a JSON array of
--   { "name": text, "ts": ISO 8601 string or UNIX time (optional), "value": any JSON }
-- Returns only the records not inserted; they are also saved in rejections.
-- No exception is caught per record (no subtransaction): an unexpected error
-- fails the whole call.
CREATE OR REPLACE FUNCTION insert_records(records jsonb, update_latest boolean DEFAULT true)
RETURNS TABLE (input_index integer, status text, cid integer, detail text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path FROM CURRENT
AS $$
#variable_conflict use_column
DECLARE
  p_records ALIAS FOR records;
  p_update_latest ALIAS FOR update_latest;
  v_now timestamptz := statement_timestamp();
  v_max_past interval;
  v_max_future interval;
  v_item jsonb;
  v_index integer;
  v_name text;
  v_ts timestamptz;
  v_type text;
  v_channel channels%ROWTYPE;
  v_status text;
  v_detail text;
  v_value double precision;
  v_value_int bigint;
  v_value_text text;
  v_value_bool boolean;
  v_value_jsonb jsonb;
  v_weeks timestamptz[] := '{}';   -- partitions already ensured in this call
  -- inserted values, for update_latest()
  l_cid integer[] := '{}';
  l_ts timestamptz[] := '{}';
  l_value double precision[] := '{}';
  l_value_int bigint[] := '{}';
  l_value_text text[] := '{}';
  l_value_bool boolean[] := '{}';
  l_value_jsonb jsonb[] := '{}';
BEGIN
  IF jsonb_typeof(p_records) IS DISTINCT FROM 'array' THEN
    RAISE EXCEPTION 'insert_records: records must be a JSON array';
  END IF;

  -- See the SHARE lock in channel.sql
  LOCK TABLE ONLY raw_records IN ROW EXCLUSIVE MODE;

  SELECT max_past, max_future INTO v_max_past, v_max_future FROM settings;

  -- Creates the partition of the next week ahead, so that the writes at the
  -- start of a week do not wait for the creation.
  PERFORM ensure_partition(partition_start(v_now, 1));
  v_weeks := ARRAY[partition_start(v_now, 1)];

  FOR v_item, v_index IN
    SELECT e, (n - 1)::integer FROM jsonb_array_elements(p_records) WITH ORDINALITY AS a(e, n)
  LOOP
    v_status := NULL;
    v_detail := NULL;
    v_channel := NULL;

    -- record format and timestamp
    IF jsonb_typeof(v_item) <> 'object'
       OR jsonb_typeof(v_item->'name') IS DISTINCT FROM 'string'
       OR btrim(v_item->>'name') = ''
       OR NOT v_item ? 'value' THEN
      v_status := 'invalid_record';
      v_detail := 'a record must be an object with a non-empty string "name" and a "value"';
    ELSE
      v_name := btrim(v_item->>'name');
      v_ts := parse_ts(v_item->'ts', v_now);
      IF v_ts IS NULL THEN
        v_status := 'invalid_record';
        v_detail := '"ts" must be an ISO 8601 string with a time zone, or UNIX time';
      ELSIF v_ts < v_now - v_max_past OR v_ts > v_now + v_max_future THEN
        v_status := 'timestamp_out_of_range';
        v_detail := format('"ts" must be within %s before and %s after now', v_max_past, v_max_future);
      END IF;
    END IF;

    -- channel valid at ts, or a guessed type for an unknown name
    IF v_status IS NULL THEN
      SELECT * INTO v_channel FROM channels
        WHERE name = v_name AND valid_from <= v_ts
        ORDER BY valid_from DESC LIMIT 1;
      IF FOUND THEN
        v_type := v_channel.type;
      ELSIF EXISTS (SELECT 1 FROM channels WHERE name = v_name) THEN
        v_status := 'out_of_validity';
        v_detail := '"ts" is before the valid_from of the channel';
      ELSE
        v_type := guess_type(v_item->'value');
        IF v_type IS NULL THEN
          v_status := 'invalid_value';
          v_detail := 'channel type cannot be guessed from this value';
        END IF;
      END IF;
    END IF;

    IF v_status IS NULL THEN
      SELECT * INTO v_status, v_detail, v_value, v_value_int, v_value_text, v_value_bool, v_value_jsonb
        FROM convert_value(v_type, v_item->'value');
    END IF;

    -- a new channel is created only after its first value is found valid
    IF v_status IS NULL AND v_channel.cid IS NULL THEN
      INSERT INTO channels (name, type) VALUES (v_name, v_type)
        ON CONFLICT (name, valid_from) DO NOTHING;
      SELECT * INTO v_channel FROM channels
        WHERE name = v_name AND valid_from <= v_ts
        ORDER BY valid_from DESC LIMIT 1;
      IF v_channel.type <> v_type THEN   -- created concurrently by another writer
        SELECT * INTO v_status, v_detail, v_value, v_value_int, v_value_text, v_value_bool, v_value_jsonb
          FROM convert_value(v_channel.type, v_item->'value');
      END IF;
    END IF;

    IF v_status IS NULL THEN
      IF partition_start(v_ts) <> ALL (v_weeks) THEN
        PERFORM ensure_partition(v_ts);
        v_weeks := v_weeks || partition_start(v_ts);
      END IF;

      INSERT INTO raw_records (cid, ts, inserted_at, value, value_int, value_text, value_bool, value_jsonb)
        VALUES (v_channel.cid, v_ts, v_now, v_value, v_value_int, v_value_text, v_value_bool, v_value_jsonb)
        ON CONFLICT (cid, ts) DO NOTHING;
      IF FOUND THEN
        l_cid := l_cid || v_channel.cid;
        l_ts := l_ts || v_ts;
        l_value := l_value || v_value;
        l_value_int := l_value_int || v_value_int;
        l_value_text := l_value_text || v_value_text;
        l_value_bool := l_value_bool || v_value_bool;
        l_value_jsonb := l_value_jsonb || v_value_jsonb;
        CONTINUE;
      END IF;
      v_status := 'duplicate';
      v_detail := 'a value with the same channel and ts already exists';
    END IF;

    INSERT INTO rejections (status, cid, detail, record)
      VALUES (v_status, v_channel.cid, v_detail, v_item);
    input_index := v_index;
    status := v_status;
    cid := v_channel.cid;
    detail := v_detail;
    RETURN NEXT;
  END LOOP;

  IF p_update_latest THEN
    PERFORM update_latest(l_cid, l_ts, v_now,
      l_value, l_value_int, l_value_text, l_value_bool, l_value_jsonb);
  END IF;
END;
$$;


-- Writes one number by name. Returns the status ('inserted' on success).
-- extra_float_digits: the double goes through JSON text, which is exact only
-- with the shortest-exact output (> 0; the default is 1).
CREATE OR REPLACE FUNCTION insert_record(name text, ts timestamptz, value double precision)
RETURNS text
LANGUAGE sql SECURITY DEFINER SET search_path FROM CURRENT SET extra_float_digits = 1
AS $$
  SELECT COALESCE(
    (SELECT r.status FROM insert_records(jsonb_build_array(jsonb_build_object(
      'name', insert_record.name, 'ts', insert_record.ts, 'value', insert_record.value))) AS r),
    'inserted')
$$;


-- Low-level, for administrators: writes to a cid directly. No type guessing,
-- no channel creation, and no check of the accepted time range (for loading
-- old data), but ts must be in the validity period of the cid.
CREATE OR REPLACE FUNCTION insert_record_by_cid(cid integer, ts timestamptz, value jsonb)
RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path FROM CURRENT
AS $$
#variable_conflict use_column
DECLARE
  p_cid ALIAS FOR cid;
  p_ts ALIAS FOR ts;
  p_value ALIAS FOR value;
  v_now timestamptz := statement_timestamp();
  v_channel channels%ROWTYPE;
  v_status text;
  v_detail text;
  v_value double precision;
  v_value_int bigint;
  v_value_text text;
  v_value_bool boolean;
  v_value_jsonb jsonb;
BEGIN
  -- See the SHARE lock in channel.sql
  LOCK TABLE ONLY raw_records IN ROW EXCLUSIVE MODE;

  SELECT * INTO v_channel FROM channels c WHERE c.cid = p_cid;
  IF NOT FOUND THEN
    v_status := 'invalid_record';
    v_detail := format('no channel with cid %s', p_cid);
  ELSIF p_ts IS NULL OR NOT isfinite(p_ts) THEN
    v_status := 'invalid_record';
    v_detail := 'ts must be a finite timestamp';
  ELSIF p_ts < v_channel.valid_from OR EXISTS (
    SELECT 1 FROM channels c
    WHERE c.name = v_channel.name AND c.valid_from > v_channel.valid_from AND c.valid_from <= p_ts
  ) THEN
    v_status := 'out_of_validity';
    v_detail := format('ts is out of the validity period of cid %s', p_cid);
  ELSE
    SELECT * INTO v_status, v_detail, v_value, v_value_int, v_value_text, v_value_bool, v_value_jsonb
      FROM convert_value(v_channel.type, p_value);
  END IF;

  IF v_status IS NULL THEN
    PERFORM ensure_partition(p_ts);
    INSERT INTO raw_records (cid, ts, inserted_at, value, value_int, value_text, value_bool, value_jsonb)
      VALUES (p_cid, p_ts, v_now, v_value, v_value_int, v_value_text, v_value_bool, v_value_jsonb)
      ON CONFLICT (cid, ts) DO NOTHING;
    IF FOUND THEN
      PERFORM update_latest(ARRAY[p_cid], ARRAY[p_ts], v_now,
        ARRAY[v_value], ARRAY[v_value_int], ARRAY[v_value_text], ARRAY[v_value_bool], ARRAY[v_value_jsonb]);
      RETURN 'inserted';
    END IF;
    v_status := 'duplicate';
    v_detail := 'a value with the same channel and ts already exists';
  END IF;

  INSERT INTO rejections (status, cid, detail, record)
    VALUES (v_status, v_channel.cid, v_detail, jsonb_build_object('cid', p_cid, 'ts', p_ts, 'value', p_value));
  RETURN v_status;
END;
$$;
