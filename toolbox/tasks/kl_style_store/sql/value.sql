-- Input value rules. See "値の型" in README_ja.md.


-- Timestamp of a record: an ISO 8601 string with date, time and time zone,
-- or UNIX time. Missing or null gives p_default. Returns NULL if not
-- acceptable; nothing is completed (no default time or time zone).
CREATE OR REPLACE FUNCTION parse_ts(p_ts jsonb, p_default timestamptz)
RETURNS timestamptz
LANGUAGE plpgsql STABLE
AS $$
DECLARE
  v_text text;
BEGIN
  IF p_ts IS NULL OR jsonb_typeof(p_ts) = 'null' THEN
    RETURN p_default;
  ELSIF jsonb_typeof(p_ts) = 'number' THEN
    IF abs(p_ts::numeric) < 1e11 THEN
      RETURN to_timestamp(p_ts::numeric::double precision);
    END IF;
  ELSIF jsonb_typeof(p_ts) = 'string' THEN
    v_text := p_ts #>> '{}';
    IF v_text ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt ][0-9]{2}:[0-9]{2}(:[0-9]{2}(\.[0-9]+)?)?([Zz]|[+-][0-9]{2}(:?[0-9]{2})?)$'
       AND pg_input_is_valid(v_text, 'timestamptz') THEN
      RETURN v_text::timestamptz;
    END IF;
  END IF;
  RETURN NULL;
END;
$$;


-- Channel type for the first value of an unknown name. NULL if it cannot be guessed.
CREATE OR REPLACE FUNCTION guess_type(p_value jsonb)
RETURNS text
LANGUAGE sql IMMUTABLE
AS $$
  SELECT CASE jsonb_typeof(p_value)
    WHEN 'number' THEN 'double'
    WHEN 'boolean' THEN 'double'
    WHEN 'string' THEN
      CASE WHEN p_value #>> '{}' IN ('NaN', 'Infinity', '-Infinity') THEN NULL ELSE 'text' END
    WHEN 'object' THEN 'json'
    WHEN 'array' THEN 'json'
  END
$$;


-- Converts p_value for a channel of p_type. On success, status is NULL and
-- exactly one of the value columns is set.
CREATE OR REPLACE FUNCTION convert_value(
  p_type text, p_value jsonb,
  OUT status text, OUT detail text,
  OUT value double precision, OUT value_int bigint, OUT value_text text,
  OUT value_bool boolean, OUT value_jsonb jsonb
)
LANGUAGE plpgsql STABLE
AS $$
DECLARE
  v_kind text := jsonb_typeof(p_value);
  v_string text;      -- for a JSON string
  v_number numeric;   -- for a JSON number or boolean (1 / 0)
BEGIN
  IF v_kind IS NULL OR v_kind = 'null' THEN
    status := 'invalid_value';
    detail := 'value is null';
    RETURN;
  END IF;

  IF v_kind = 'string' THEN
    v_string := p_value #>> '{}';
  ELSIF v_kind = 'number' THEN
    v_number := p_value::numeric;
  ELSIF v_kind = 'boolean' THEN
    v_number := CASE WHEN p_value::boolean THEN 1 ELSE 0 END;
  END IF;

  IF p_type = 'text' THEN
    value_text := COALESCE(v_string, p_value::text);
  ELSIF p_type = 'json' THEN
    value_jsonb := p_value;

  -- numeric types below
  ELSIF v_string IN ('NaN', 'Infinity', '-Infinity') THEN
    status := 'invalid_value';
    detail := 'value is not finite';
  ELSIF v_number IS NULL THEN
    status := 'type_mismatch';
    detail := format('%s value for a %s channel', v_kind, p_type);
  ELSIF p_type = 'double' THEN
    IF pg_input_is_valid(v_number::text, 'double precision') THEN
      value := v_number::double precision;
    ELSE
      status := 'invalid_value';
      detail := 'value is out of the range of double precision';
    END IF;
  ELSIF p_type = 'integer' THEN
    IF v_number <> trunc(v_number) THEN
      status := 'type_mismatch';
      detail := 'non-integer value for an integer channel';
    ELSIF v_number NOT BETWEEN -9223372036854775808 AND 9223372036854775807 THEN
      status := 'invalid_value';
      detail := 'value is out of the range of bigint';
    ELSE
      value_int := v_number::bigint;
    END IF;
  ELSIF p_type = 'boolean' THEN
    IF v_number IN (0, 1) THEN
      value_bool := (v_number = 1);
    ELSE
      status := 'type_mismatch';
      detail := 'number other than 0 or 1 for a boolean channel';
    END IF;
  END IF;
END;
$$;


-- A stored value as JSON, the inverse of convert_value(). Used to convert
-- records between channel types and to save removed records in rejections.
-- A double is exact only with extra_float_digits > 0 (the default is 1);
-- the callers set it.
CREATE OR REPLACE FUNCTION stored_value(
  p_value double precision, p_value_int bigint, p_value_text text,
  p_value_bool boolean, p_value_jsonb jsonb
)
RETURNS jsonb
LANGUAGE sql IMMUTABLE
AS $$
  SELECT COALESCE(to_jsonb(p_value), to_jsonb(p_value_int), to_jsonb(p_value_text),
                  to_jsonb(p_value_bool), p_value_jsonb)
$$;
