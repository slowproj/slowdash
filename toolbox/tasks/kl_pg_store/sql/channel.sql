-- Channel management. See "Channelの管理" in README_ja.md for the cases
-- each function is for.
--
-- The functions that change which channel a record belongs to (by ts or by
-- name) take "LOCK TABLE ONLY raw_records IN SHARE MODE". It conflicts with
-- the ROW EXCLUSIVE lock taken by the insert functions: it waits for the
-- in-flight writers, and holds new writers until commit, so that no record
-- is routed by the old channel definitions after the change.


-- Serializes the management functions on channels sharing a name.
CREATE OR REPLACE FUNCTION lock_channel_name(p_name text)
RETURNS void
LANGUAGE sql
AS $$
  SELECT pg_advisory_xact_lock(hashtextextended('channel:' || current_schema() || '.' || p_name, 0))
$$;


-- Records every change of channels, also by direct SQL.
CREATE OR REPLACE FUNCTION log_channel_change()
RETURNS trigger
LANGUAGE plpgsql SET search_path FROM CURRENT
AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    INSERT INTO channel_log (operation, cid, new) VALUES ('insert', NEW.cid, to_jsonb(NEW));
  ELSIF TG_OP = 'UPDATE' THEN
    INSERT INTO channel_log (operation, cid, old, new) VALUES ('update', NEW.cid, to_jsonb(OLD), to_jsonb(NEW));
  ELSE
    INSERT INTO channel_log (operation, cid, old) VALUES ('delete', OLD.cid, to_jsonb(OLD));
  END IF;
  RETURN NULL;
END;
$$;

CREATE OR REPLACE TRIGGER channels_log
  AFTER INSERT OR UPDATE OR DELETE ON channels
  FOR EACH ROW EXECUTE FUNCTION log_channel_change();


-- Moves the records of p_from in [p_ts_from, p_ts_to) to p_to, converting
-- the values if the types differ. Raises an error if any value cannot be
-- converted, or if an integer is not exact in double precision (beyond
-- 2**53) unless p_allow_rounding. A record whose ts already exists in p_to
-- is moved to rejections as duplicate (the value in p_to wins, as for any
-- duplicate). The caller holds the SHARE lock on raw_records and updates
-- raw_latest.
CREATE OR REPLACE FUNCTION move_records(
  p_from channels, p_to channels, p_ts_from timestamptz, p_ts_to timestamptz,
  p_allow_rounding boolean,
  OUT moved bigint, OUT duplicates bigint
)
LANGUAGE plpgsql SET search_path FROM CURRENT SET extra_float_digits = 1
AS $$
DECLARE
  v_ts timestamptz;
  v_detail text;
BEGIN
  -- Narrows the range to the records actually there, so that the statements
  -- below (planned with these values) scan only their partitions; the range
  -- on t is not implied by t.ts = r.ts, and the duplicate check would read
  -- the whole history of p_to (e.g. merge_channel() over all time).
  SELECT min(ts), max(ts) + interval '1 microsecond' INTO p_ts_from, p_ts_to
    FROM raw_records WHERE cid = p_from.cid AND ts >= p_ts_from AND ts < p_ts_to;
  IF p_ts_from IS NULL THEN
    moved := 0;
    duplicates := 0;
    RETURN;
  END IF;

  WITH d AS (
    DELETE FROM raw_records r
    WHERE r.cid = p_from.cid AND r.ts >= p_ts_from AND r.ts < p_ts_to
      AND EXISTS (SELECT 1 FROM raw_records t
                  WHERE t.cid = p_to.cid AND t.ts = r.ts AND t.ts >= p_ts_from AND t.ts < p_ts_to)
    RETURNING r.*
  )
  INSERT INTO rejections (status, cid, detail, record)
  SELECT 'duplicate', p_from.cid,
    format('moving to cid %s: a value with the same ts already exists', p_to.cid),
    jsonb_build_object('name', p_from.name, 'ts', d.ts,
      'value', stored_value(d.value, d.value_int, d.value_text, d.value_bool, d.value_jsonb),
      'cid', d.cid, 'inserted_at', d.inserted_at)
  FROM d;
  GET DIAGNOSTICS duplicates = ROW_COUNT;

  IF p_from.type = p_to.type THEN
    UPDATE raw_records SET cid = p_to.cid
      WHERE cid = p_from.cid AND ts >= p_ts_from AND ts < p_ts_to;
    GET DIAGNOSTICS moved = ROW_COUNT;
    RETURN;
  END IF;

  SELECT r.ts, cv.detail INTO v_ts, v_detail
  FROM raw_records r
  CROSS JOIN LATERAL convert_value(p_to.type,
    stored_value(r.value, r.value_int, r.value_text, r.value_bool, r.value_jsonb)) cv
  WHERE r.cid = p_from.cid AND r.ts >= p_ts_from AND r.ts < p_ts_to AND cv.status IS NOT NULL
  LIMIT 1;
  IF FOUND THEN
    RAISE EXCEPTION 'cannot convert the value at % of cid % (%) to %: %',
      v_ts, p_from.cid, p_from.type, p_to.type, v_detail;
  END IF;

  -- Only an integer channel is checked: a JSON number may be a double
  -- already, whose decimal text is not exact either.
  IF p_from.type = 'integer' AND p_to.type = 'double' AND NOT p_allow_rounding THEN
    SELECT r.ts, r.value_int::text INTO v_ts, v_detail
    FROM raw_records r
    WHERE r.cid = p_from.cid AND r.ts >= p_ts_from AND r.ts < p_ts_to
      AND r.value_int NOT BETWEEN -9007199254740992 AND 9007199254740992
      AND CASE WHEN abs(r.value_int::double precision) >= 9223372036854775808 THEN true
               ELSE r.value_int::double precision::bigint <> r.value_int END
    LIMIT 1;
    IF FOUND THEN
      RAISE EXCEPTION 'the value % at % of cid % is not exact in double precision; use allow_rounding => true to round',
        v_detail, v_ts, p_from.cid;
    END IF;
  END IF;

  WITH m AS (
    DELETE FROM raw_records
    WHERE cid = p_from.cid AND ts >= p_ts_from AND ts < p_ts_to
    RETURNING *
  )
  INSERT INTO raw_records (cid, ts, inserted_at, value, value_int, value_text, value_bool, value_jsonb)
  SELECT p_to.cid, m.ts, m.inserted_at, cv.value, cv.value_int, cv.value_text, cv.value_bool, cv.value_jsonb
  FROM m
  CROSS JOIN LATERAL convert_value(p_to.type,
    stored_value(m.value, m.value_int, m.value_text, m.value_bool, m.value_jsonb)) cv;
  GET DIAGNOSTICS moved = ROW_COUNT;
END;
$$;


-- Creates a new name. If the name already exists with the same type, does
-- nothing and returns its current cid (for start-up scripts); unit and
-- description are changed only by describe_channel(). NULL unit is not
-- written yet; '' is no unit (e.g. a ratio).
CREATE OR REPLACE FUNCTION create_channel(
  name text,
  type text DEFAULT 'double',
  unit text DEFAULT NULL,
  description text DEFAULT NULL
)
RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path FROM CURRENT
AS $$
#variable_conflict use_column
DECLARE
  p_name ALIAS FOR name;
  p_type ALIAS FOR type;
  p_unit ALIAS FOR unit;
  p_description ALIAS FOR description;
  v_name text := btrim(p_name);
  v_channel channels%ROWTYPE;
  v_cid integer;
BEGIN
  IF v_name IS NULL OR v_name = '' THEN
    RAISE EXCEPTION 'create_channel: name must not be empty';
  END IF;
  PERFORM lock_channel_name(v_name);

  SELECT * INTO v_channel FROM channels WHERE name = v_name ORDER BY valid_from DESC LIMIT 1;
  IF NOT FOUND THEN
    INSERT INTO channels (name, type, unit, description)
      VALUES (v_name, p_type, p_unit, p_description)
      ON CONFLICT (name, valid_from) DO NOTHING
      RETURNING cid INTO v_cid;
    IF v_cid IS NOT NULL THEN
      RETURN v_cid;
    END IF;
    -- created concurrently by a writer
    SELECT * INTO v_channel FROM channels WHERE name = v_name ORDER BY valid_from DESC LIMIT 1;
  END IF;

  IF v_channel.type <> p_type THEN
    RAISE EXCEPTION 'create_channel: channel "%" already exists as type %; use replace_channel() to change it',
      v_name, v_channel.type;
  END IF;
  IF p_unit IS DISTINCT FROM v_channel.unit AND p_unit IS NOT NULL
     OR p_description IS DISTINCT FROM v_channel.description AND p_description IS NOT NULL THEN
    RAISE WARNING 'create_channel: channel "%" already exists with other unit or description; use describe_channel() to change them',
      v_name;
  END IF;
  RETURN v_channel.cid;
END;
$$;


-- Sets unit and description of a cid as given. NULL is not described yet
-- (as created automatically); '' is described as empty (e.g. no unit).
CREATE OR REPLACE FUNCTION describe_channel(cid integer, unit text, description text)
RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path FROM CURRENT
AS $$
#variable_conflict use_column
DECLARE
  p_cid ALIAS FOR cid;
  p_unit ALIAS FOR unit;
  p_description ALIAS FOR description;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM channels WHERE cid = p_cid) THEN
    RAISE EXCEPTION 'describe_channel: no channel with cid %', p_cid;
  END IF;
  UPDATE channels SET unit = p_unit, description = p_description
  WHERE cid = p_cid AND (unit, description) IS DISTINCT FROM (p_unit, p_description);
  RETURN p_cid;
END;
$$;

-- Same, for the current (latest valid_from) channel of a name
CREATE OR REPLACE FUNCTION describe_channel(name text, unit text, description text)
RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path FROM CURRENT
AS $$
#variable_conflict use_column
DECLARE
  p_name ALIAS FOR name;
  p_unit ALIAS FOR unit;
  p_description ALIAS FOR description;
  v_cid integer;
BEGIN
  SELECT cid INTO v_cid FROM channels WHERE name = btrim(p_name) ORDER BY valid_from DESC LIMIT 1;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'describe_channel: no channel "%"', p_name;
  END IF;
  RETURN describe_channel(v_cid, p_unit, p_description);
END;
$$;


-- From valid_from on, records of name belong to a new channel (new cid).
-- type, unit and description are inherited if not given. If valid_from is
-- in the past, the records at or after it are moved to the new channel
-- (see move_records() for allow_rounding). Returns the new cid.
CREATE OR REPLACE FUNCTION replace_channel(
  name text,
  valid_from timestamptz,
  type text DEFAULT NULL,
  unit text DEFAULT NULL,
  description text DEFAULT NULL,
  allow_rounding boolean DEFAULT false
)
RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path FROM CURRENT
AS $$
#variable_conflict use_column
DECLARE
  p_name ALIAS FOR name;
  p_valid_from ALIAS FOR valid_from;
  p_type ALIAS FOR type;
  p_unit ALIAS FOR unit;
  p_description ALIAS FOR description;
  p_allow_rounding ALIAS FOR allow_rounding;
  v_name text := btrim(p_name);
  v_prev channels%ROWTYPE;
  v_new channels%ROWTYPE;
  v_moved record;
BEGIN
  IF p_valid_from IS NULL OR NOT isfinite(p_valid_from) THEN
    RAISE EXCEPTION 'replace_channel: valid_from must be a finite timestamp';
  END IF;
  PERFORM lock_channel_name(v_name);
  LOCK TABLE ONLY raw_records IN SHARE MODE;

  -- the channel whose period contains valid_from
  SELECT * INTO v_prev FROM channels
    WHERE name = v_name AND valid_from <= p_valid_from
    ORDER BY valid_from DESC LIMIT 1;
  IF NOT FOUND THEN
    IF EXISTS (SELECT 1 FROM channels WHERE name = v_name) THEN
      RAISE EXCEPTION 'replace_channel: % is before the first valid_from of "%"', p_valid_from, v_name;
    END IF;
    RAISE EXCEPTION 'replace_channel: no channel "%"; use create_channel()', v_name;
  END IF;
  IF v_prev.valid_from = p_valid_from THEN
    RAISE EXCEPTION 'replace_channel: channel "%" (cid %) already starts at %', v_name, v_prev.cid, p_valid_from;
  END IF;

  INSERT INTO channels (name, valid_from, type, unit, description)
    VALUES (v_name, p_valid_from, COALESCE(p_type, v_prev.type),
            COALESCE(p_unit, v_prev.unit), COALESCE(p_description, v_prev.description))
    RETURNING * INTO v_new;

  -- The records of v_prev are all before the next valid_from, so the upper
  -- bound is not needed.
  SELECT * INTO v_moved FROM move_records(v_prev, v_new, p_valid_from, 'infinity', p_allow_rounding);
  IF v_moved.moved > 0 THEN
    PERFORM rebuild_latest(v_prev.cid);
    PERFORM rebuild_latest(v_new.cid);
  END IF;

  INSERT INTO channel_log (operation, cid, detail)
    VALUES ('replace_channel', v_new.cid,
      format('"%s" from %s replaces cid %s; %s records moved', v_name, p_valid_from, v_prev.cid, v_moved.moved));
  RETURN v_new.cid;
END;
$$;


-- Renames all the channels of a name; their whole history follows the new name.
-- Writers still sending the old name will create a new channel.
CREATE OR REPLACE FUNCTION rename_channel(old_name text, new_name text)
RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path FROM CURRENT
AS $$
#variable_conflict use_column
DECLARE
  p_old_name ALIAS FOR old_name;
  p_new_name ALIAS FOR new_name;
  v_old_name text := btrim(p_old_name);
  v_new_name text := btrim(p_new_name);
  v_count integer;
BEGIN
  IF v_new_name IS NULL OR v_new_name = '' THEN
    RAISE EXCEPTION 'rename_channel: name must not be empty';
  END IF;
  PERFORM lock_channel_name(least(v_old_name, v_new_name));
  PERFORM lock_channel_name(greatest(v_old_name, v_new_name));
  LOCK TABLE ONLY raw_records IN SHARE MODE;

  IF EXISTS (SELECT 1 FROM channels WHERE name = v_new_name) THEN
    RAISE EXCEPTION 'rename_channel: channel "%" already exists; use merge_channel() to move records into it', v_new_name;
  END IF;
  UPDATE channels SET name = v_new_name WHERE name = v_old_name;
  GET DIAGNOSTICS v_count = ROW_COUNT;
  IF v_count = 0 THEN
    RAISE EXCEPTION 'rename_channel: no channel "%"', v_old_name;
  END IF;
  RETURN v_count;
END;
$$;

-- Moves one channel (one period of a name) to a new name, where it becomes
-- valid for all time (valid_from = -infinity). The rest of the old name is
-- unchanged: a record of the old name in this period is now routed to the
-- previous period, or rejected as out_of_validity if there is none.
CREATE OR REPLACE FUNCTION rename_channel(cid integer, new_name text)
RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path FROM CURRENT
AS $$
#variable_conflict use_column
DECLARE
  p_cid ALIAS FOR cid;
  p_new_name ALIAS FOR new_name;
  v_new_name text := btrim(p_new_name);
  v_channel channels%ROWTYPE;
BEGIN
  IF v_new_name IS NULL OR v_new_name = '' THEN
    RAISE EXCEPTION 'rename_channel: name must not be empty';
  END IF;
  SELECT * INTO v_channel FROM channels WHERE cid = p_cid;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'rename_channel: no channel with cid %', p_cid;
  END IF;
  PERFORM lock_channel_name(least(v_channel.name, v_new_name));
  PERFORM lock_channel_name(greatest(v_channel.name, v_new_name));
  LOCK TABLE ONLY raw_records IN SHARE MODE;

  IF EXISTS (SELECT 1 FROM channels WHERE name = v_new_name) THEN
    RAISE EXCEPTION 'rename_channel: channel "%" already exists; use merge_channel() to move records into it', v_new_name;
  END IF;
  UPDATE channels SET name = v_new_name, valid_from = '-infinity' WHERE cid = p_cid;
  RETURN p_cid;
END;
$$;


-- Moves all the records of cid into the channels of into_name (each
-- record to the channel valid at its ts), and deletes cid. into_name
-- may be the name of cid itself, to undo replace_channel(). Values are
-- converted as in replace_channel(); duplicates go to rejections.
-- Returns the number of records moved.
CREATE OR REPLACE FUNCTION merge_channel(cid integer, into_name text, allow_rounding boolean DEFAULT false)
RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER SET search_path FROM CURRENT
AS $$
#variable_conflict use_column
DECLARE
  p_cid ALIAS FOR cid;
  p_into_name ALIAS FOR into_name;
  p_allow_rounding ALIAS FOR allow_rounding;
  v_into text := btrim(p_into_name);
  v_src channels%ROWTYPE;
  v_period record;
  v_target channels%ROWTYPE;
  v_first timestamptz;
  v_result record;
  v_moved bigint := 0;
  v_duplicates bigint := 0;
BEGIN
  SELECT * INTO v_src FROM channels WHERE cid = p_cid;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'merge_channel: no channel with cid %', p_cid;
  END IF;
  PERFORM lock_channel_name(least(v_src.name, v_into));
  PERFORM lock_channel_name(greatest(v_src.name, v_into));
  LOCK TABLE ONLY raw_records IN SHARE MODE;

  DELETE FROM channels WHERE cid = p_cid;
  SELECT min(valid_from) INTO v_first FROM channels WHERE name = v_into;
  IF v_first IS NULL THEN
    IF v_into = v_src.name THEN
      RAISE EXCEPTION 'merge_channel: cid % is the only channel of "%"', p_cid, v_into;
    END IF;
    RAISE EXCEPTION 'merge_channel: no channel "%"; use rename_channel() instead', v_into;
  END IF;
  IF EXISTS (SELECT 1 FROM raw_records WHERE cid = p_cid AND ts < v_first) THEN
    RAISE EXCEPTION 'merge_channel: cid % has records before the first valid_from of "%" (%)', p_cid, v_into, v_first;
  END IF;

  FOR v_period IN
    SELECT c AS channel, lead(c.valid_from, 1, 'infinity') OVER (ORDER BY c.valid_from) AS valid_to
    FROM channels c WHERE c.name = v_into
  LOOP
    v_target := v_period.channel;
    SELECT * INTO v_result FROM move_records(v_src, v_target, v_target.valid_from, v_period.valid_to, p_allow_rounding);
    IF v_result.moved > 0 THEN
      PERFORM rebuild_latest(v_target.cid);
    END IF;
    v_moved := v_moved + v_result.moved;
    v_duplicates := v_duplicates + v_result.duplicates;
  END LOOP;
  DELETE FROM raw_latest WHERE cid = p_cid;

  INSERT INTO channel_log (operation, cid, detail)
    VALUES ('merge_channel', p_cid,
      format('cid %s ("%s") merged into "%s"; %s records moved, %s duplicates to rejections',
        p_cid, v_src.name, v_into, v_moved, v_duplicates));
  RETURN v_moved;
END;
$$;


-- Deletes a channel. Its records are moved to rejections (status 'dropped'),
-- in the input format of insert_records(). Returns the number of records.
CREATE OR REPLACE FUNCTION drop_channel(cid integer)
RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER SET search_path FROM CURRENT SET extra_float_digits = 1
AS $$
#variable_conflict use_column
DECLARE
  p_cid ALIAS FOR cid;
  v_channel channels%ROWTYPE;
  v_count bigint;
BEGIN
  SELECT * INTO v_channel FROM channels WHERE cid = p_cid;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'drop_channel: no channel with cid %', p_cid;
  END IF;
  PERFORM lock_channel_name(v_channel.name);
  LOCK TABLE ONLY raw_records IN SHARE MODE;

  WITH d AS (
    DELETE FROM raw_records WHERE cid = p_cid RETURNING *
  )
  INSERT INTO rejections (status, cid, detail, record)
  SELECT 'dropped', p_cid, 'drop_channel()',
    jsonb_build_object('name', v_channel.name, 'ts', d.ts,
      'value', stored_value(d.value, d.value_int, d.value_text, d.value_bool, d.value_jsonb),
      'cid', d.cid, 'inserted_at', d.inserted_at)
  FROM d;
  GET DIAGNOSTICS v_count = ROW_COUNT;

  DELETE FROM raw_latest WHERE cid = p_cid;
  DELETE FROM channels WHERE cid = p_cid;

  INSERT INTO channel_log (operation, cid, detail)
    VALUES ('drop_channel', p_cid,
      format('cid %s ("%s") dropped; %s records moved to rejections', p_cid, v_channel.name, v_count));
  RETURN v_count;
END;
$$;
