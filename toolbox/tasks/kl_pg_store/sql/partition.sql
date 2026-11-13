-- Start of the weekly partition containing p_ts (Monday 00:00 UTC), or of
-- the one p_weeks later. Computed on the UTC wall clock, so that the session
-- time zone (DST) does not matter.
CREATE OR REPLACE FUNCTION partition_start(p_ts timestamptz, p_weeks integer DEFAULT 0)
RETURNS timestamptz
LANGUAGE sql IMMUTABLE
AS $$
  SELECT (date_trunc('week', p_ts AT TIME ZONE 'UTC') + make_interval(weeks => p_weeks)) AT TIME ZONE 'UTC'
$$;


-- Creates the partition for p_ts if missing. Returns true if created.
CREATE OR REPLACE FUNCTION ensure_partition(p_ts timestamptz)
RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path FROM CURRENT
AS $$
DECLARE
  v_from timestamptz := partition_start(p_ts);
  v_name text := 'raw_records_' || to_char(v_from AT TIME ZONE 'UTC', 'YYYYMMDD');
BEGIN
  IF to_regclass(quote_ident(v_name)) IS NOT NULL THEN
    RETURN false;
  END IF;

  -- Serializes the creators. Taken anyway by ATTACH PARTITION below; it does
  -- not block reads or writes. Unlike an advisory lock, acquiring a table lock
  -- refreshes the catalog cache, so the check below sees a partition just
  -- committed by another creator.
  LOCK TABLE ONLY raw_records IN SHARE UPDATE EXCLUSIVE MODE;
  IF to_regclass(quote_ident(v_name)) IS NOT NULL THEN
    RETURN false;
  END IF;

  -- "CREATE TABLE ... PARTITION OF" would take an ACCESS EXCLUSIVE lock on
  -- raw_records until commit, blocking all readers and writers.
  -- ATTACH PARTITION takes only SHARE UPDATE EXCLUSIVE.
  EXECUTE format(
    'CREATE TABLE %I (LIKE raw_records INCLUDING DEFAULTS INCLUDING CONSTRAINTS)',
    v_name
  );
  EXECUTE format(
    'ALTER TABLE raw_records ATTACH PARTITION %I FOR VALUES FROM (%L) TO (%L)',
    v_name, v_from, partition_start(p_ts, 1)
  );
  RETURN true;
END;
$$;


-- Creates the partitions of this week and the next weeks weeks. Returns
-- the number of partitions created. For people and external scripts;
-- insert_records() creates the partitions it needs by itself.
CREATE OR REPLACE FUNCTION ensure_partitions(weeks integer DEFAULT 4)
RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path FROM CURRENT
AS $$
DECLARE
  p_weeks ALIAS FOR weeks;
  v_now timestamptz := statement_timestamp();
  v_created integer := 0;
BEGIN
  IF p_weeks IS NULL OR p_weeks NOT BETWEEN 0 AND 10000 THEN
    RAISE EXCEPTION 'ensure_partitions: the number of weeks must be from 0 to 10000';
  END IF;
  FOR i IN 0..p_weeks LOOP
    IF ensure_partition(partition_start(v_now, i)) THEN
      v_created := v_created + 1;
    END IF;
  END LOOP;
  RETURN v_created;
END;
$$;
