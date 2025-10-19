---
--- Create a database for our values
---

CREATE DATABASE sensor_data WITH TEMPLATE = template0;

\connect sensor_data

-- table for storing doubles
-- NOTE: this design is very bad and only used as an example for easy
--       demonstration a production system probably wants to map sensor names
--       onto IDs may want to allow annotations of entries, may want annotation
--       of sensors, etc.

DROP TABLE IF EXISTS numeric_data;
CREATE TABLE numeric_data (
  sensor_name text NOT NULL,
  "timestamp" timestamp with time zone NOT NULL default now(),
  value_raw double precision NOT NULL,
  value_cal double precision
);
