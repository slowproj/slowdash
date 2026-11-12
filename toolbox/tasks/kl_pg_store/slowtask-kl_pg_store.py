# kl_pg_store: stores "data.store.>" DataPackets into PostgreSQL. See README_ja.md.
#
# Parameters:
#   dsn: PostgreSQL URL of the writer role (required)
#   schema: schema given to install.sql (default: kl_store)
#   spool: JSON Lines file for messages that could not be written (default: kl_pg_store-spool.jsonl)

import fcntl
import json
import logging
import math
import os
import time

import asyncpg
from slowpy.mesh import Tasklet

import kl_channel_page


# an error in a function called from the page is shown in the browser, without stopping the task
tasklet = Tasklet(stop_on_error=False)
pool = None
schema = None
insert_sql = None
spool_path = None

# the Slowdash HTML panel "kl_channels" (see kl_channel_page.py)
kl_channel_page.setup(tasklet, lambda: (pool, schema))


def to_json_value(x):
    # numpy scalars to Python numbers and bools, numpy arrays to lists
    if hasattr(x, 'tolist') and not isinstance(x, (str, bytes, list, tuple, dict)):
        x = x.tolist()
    # JSON cannot carry NaN or Infinity; the DB rejects these strings as non-finite values
    if isinstance(x, float) and not math.isfinite(x):
        return 'NaN' if math.isnan(x) else ('Infinity' if x > 0 else '-Infinity')
    if isinstance(x, dict):
        return { k: to_json_value(v) for k, v in x.items() }
    if isinstance(x, (list, tuple)):
        return [ to_json_value(v) for v in x ]
    return x


def to_records(body):
    records = []
    for name, data in body.items():
        t = to_json_value(data.get('t')) if isinstance(data, dict) else None   # numpy numbers as UNIX time
        if not isinstance(data, dict) or ('x' not in data and not isinstance(t, list)):
            # not a DataPacket (e.g. a TimeSeries without "t" from slowpy); without
            # "value", the DB keeps it in rejections as invalid_record
            records.append({ 'name': name, 'packet': to_json_value(data) })
            continue
        if isinstance(t, list):
            # time-series: { 't': [...], 'start': t0, field: [...], ... }
            start = to_json_value(data.get('start', 0))
            for field, values in data.items():
                if field in ('t', 'start', 'length'):
                    continue
                channel = name if field == 'x' else f'{name}.{field}'
                for ti, x in zip(t, values):
                    if x is not None:
                        records.append({ 'name': channel, 'ts': start + ti, 'value': to_json_value(x) })
        else:
            records.append({ 'name': name, 'ts': t, 'value': to_json_value(data.get('x')) })
    return records


def write_spool(payload):
    # utils/replay_spool.py renames the spool file while holding the same lock,
    # so a line is never written to a file that is already being replayed
    with open(spool_path + '.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        created = not os.path.exists(spool_path)
        with open(spool_path, 'a') as f:
            f.write(payload + '\n')
            f.flush()
            os.fsync(f.fileno())
        if created:
            # without this, a new file can disappear on a power loss
            fd = os.open(os.path.dirname(os.path.abspath(spool_path)), os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)


@tasklet.initialize()
async def initialize(params):
    global pool, schema, insert_sql, spool_path
    schema = '"%s"' % params.get('schema', 'kl_store').replace('"', '""')
    insert_sql = f'SELECT input_index, status, cid, detail FROM {schema}.insert_records($1::jsonb)'
    spool_path = params.get('spool', 'kl_pg_store-spool.jsonl')

    # min_size=0: starts even if the DB is down; connects on the first write
    pool = await asyncpg.create_pool(dsn=params['dsn'], min_size=0, max_size=1, command_timeout=15)


@tasklet.mesh.on('data.store.>')
async def store(headers, body):
    received_at = time.time()
    try:
        records = to_records(body)
    except Exception as e:
        # not a DataPacket; kept in rejections as invalid_record
        logging.error(f'kl_pg_store: invalid message: {e}')
        records = [ { 'packet': to_json_value(body) } ]
    if len(records) == 0:
        return
    payload = json.dumps(records, default=str)

    try:
        rejected = await pool.fetch(insert_sql, payload)
    except Exception as e:
        logging.error(f'kl_pg_store: DB write failed, the message is spooled to {spool_path}: {e}')
        # the DB would use the replay time for a missing ts
        for record in records:
            if record.get('ts') is None and 'value' in record:
                record['ts'] = received_at
        write_spool(json.dumps(records, default=str))
        return

    for row in rejected:
        record = records[row['input_index']]
        logging.warning(f'kl_pg_store: rejected ({row["status"]}): {record.get("name")}: {row["detail"]}')


@tasklet.finalize()
async def finalize():
    if pool is not None:
        await pool.close()


if __name__ == '__main__':
    tasklet.run(mesh_url='slowmq://localhost:18881')
