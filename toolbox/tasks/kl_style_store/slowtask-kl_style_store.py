# kl_style_store: stores "data.store.>" DataPackets into PostgreSQL. See README_ja.md.
#
# Parameters:
#   dsn: PostgreSQL URL of the writer role (required)
#   schema: schema given to install.sql (default: kl_store)
#   spool: JSON Lines file for messages that could not be written (default: kl_style_store-spool.jsonl)

import html
import json
import logging
import math
import os
import time
import urllib.parse

import asyncpg
from slowpy.mesh import Tasklet


tasklet = Tasklet()
pool = None
schema = None
insert_sql = None
spool_path = None


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
        if not isinstance(data, dict):
            # not a DataPacket; without "value", the DB keeps it in rejections as invalid_record
            records.append({ 'name': name, 'packet': to_json_value(data) })
            continue
        t = to_json_value(data.get('t'))   # numpy numbers as UNIX time
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
    with open(spool_path, 'a') as f:
        f.write(payload + '\n')
        f.flush()
        os.fsync(f.fileno())


@tasklet.initialize()
async def initialize(params):
    global pool, schema, insert_sql, spool_path
    schema = '"%s"' % params.get('schema', 'kl_store').replace('"', '""')
    insert_sql = f'SELECT input_index, status, cid, detail FROM {schema}.insert_records($1::jsonb)'
    spool_path = params.get('spool', 'kl_style_store-spool.jsonl')

    # min_size=0: starts even if the DB is down; connects on the first write
    pool = await asyncpg.create_pool(dsn=params['dsn'], min_size=0, max_size=1, command_timeout=15)


@tasklet.mesh.on('data.store.>')
async def store(headers, body):
    received_at = time.time()
    try:
        records = to_records(body)
    except Exception as e:
        # not a DataPacket; kept in rejections as invalid_record
        logging.error(f'kl_style_store: invalid message: {e}')
        records = [ { 'packet': to_json_value(body) } ]
    if len(records) == 0:
        return
    payload = json.dumps(records, default=str)

    try:
        rejected = await pool.fetch(insert_sql, payload)
    except Exception as e:
        logging.error(f'kl_style_store: DB write failed, the message is spooled to {spool_path}: {e}')
        # the DB would use the replay time for a missing ts
        for record in records:
            if record.get('ts') is None and 'value' in record:
                record['ts'] = received_at
        write_spool(json.dumps(records, default=str))
        return

    for row in rejected:
        record = records[row['input_index']]
        logging.warning(f'kl_style_store: rejected ({row["status"]}): {record.get("name")}: {row["detail"]}')


#### Channel page: a Slowdash HTML panel to list channels and edit them ####

# Errors are returned, not raised: an exception in an exported function stops the task.

@tasklet.mesh.export()
async def describe_channel(cid:int, unit:str, description:str):
    # as written: an empty input is ''
    try:
        await pool.execute(f'SELECT {schema}.describe_channel($1::integer, $2::text, $3::text)', cid, unit.strip(), description.strip())
    except Exception as e:
        return str(e)
    return 'ok'


@tasklet.mesh.export()
async def create_channel(name:str, type:str, unit:str, description:str):
    try:
        cid = await pool.fetchval(f'SELECT {schema}.create_channel($1::text, $2::text, $3::text, $4::text)', name.strip(), type, unit.strip(), description.strip())
    except Exception as e:
        return str(e)
    return f'cid {cid}'


# The filter of the page; shared by all the viewers (the page cannot keep a state)
page_filter = { 'name': '', 'show': 'unfilled' }
PAGE_MAX_ROWS = 50


@tasklet.mesh.export()
async def filter_channels(name:str, show:str):
    page_filter['name'] = name.strip()
    page_filter['show'] = show
    return 'ok'


PAGE_STYLE = """
<style>
  .kl-ch { font-size: 110%; }
  .kl-ch input, .kl-ch select { font-size: 100%; }
  .kl-ch .table { display: table; border-collapse: collapse; }
  .kl-ch .row { display: table-row; }
  .kl-ch .row > * { display: table-cell; padding: 2px 8px; border-bottom: 1px solid rgba(128,128,128,0.3); vertical-align: middle; }
  .kl-ch .head > * { font-weight: bold; }
  .kl-ch .num { text-align: right; }
  .kl-ch .dim { opacity: 0.6; }
  .kl-ch .small { font-size: 80%; }
  .kl-ch a.button { padding: 1px 8px; border: 1px solid rgba(128,128,128,0.6); border-radius: 4px; text-decoration: none; }
</style>
"""


@tasklet.content('config/html-kl_channels.html')
async def channel_page():
    name, show = page_filter['name'], page_filter['show']
    try:
        rows = await pool.fetch(f'''
            SELECT c.cid, c.name, NULLIF(c.valid_from::text, '-infinity') AS valid_from, c.type, c.unit, c.description,
              left(COALESCE(l.value::text, l.value_int::text, l.value_bool::text, l.value_text, l.value_jsonb::text), 30) AS last_value,
              to_char(l.ts, 'YYYY-MM-DD HH24:MI:SS TZH') AS last_ts,
              to_char(l.inserted_at, 'YYYY-MM-DD HH24:MI:SS TZH') AS last_inserted_at,
              extract(epoch FROM l.ts)::float8 AS last_epoch, l.ts < now() - interval '1 hour' AS stopped,
              count(*) OVER () AS matched
            FROM {schema}.channels c LEFT JOIN {schema}.raw_latest l USING (cid)
            WHERE strpos(lower(c.name), lower($1)) > 0
              AND ($2 <> 'unfilled' OR c.unit IS NULL OR c.description IS NULL)
            ORDER BY c.name, c.valid_from
            LIMIT {PAGE_MAX_ROWS}
        ''', name, show)
        total = await pool.fetchval(f'SELECT count(*) FROM {schema}.channels')
    except Exception as e:
        return f'<p>kl_style_store: DB error: {html.escape(str(e))}</p>'

    def attr(x):
        return html.escape('' if x is None else str(x), quote=True)

    def unfilled(x):
        # NULL (not described yet) is shown as a placeholder; Set writes it as ''
        return ' placeholder="unfilled"' if x is None else ''

    matched = rows[0]['matched'] if len(rows) > 0 else 0
    types = ''.join(f'<option>{t}</option>' for t in ('double', 'integer', 'boolean', 'text', 'json'))
    shows = ''.join(
        f'<option value="{v}"{" selected" if v == show else ""}>{label}</option>'
        for v, label in (('unfilled', 'without unit or description'), ('all', 'all'))
    )
    lines = [
        PAGE_STYLE,
        '<div class="kl-ch">',
        '<h3>New channel</h3>',
        '<form>',
        '  <input name="name" placeholder="name" size="40">',
        f'  <select name="type">{types}</select>',
        '  <input name="unit" placeholder="unit" size="8">',
        '  <input name="description" placeholder="description" size="40">',
        '  <input type="submit" name="kl_style_store.create_channel()" value="Create">',
        '</form>',
        '<h3>Channels</h3>',
        '<form>',
        f'  name contains <input name="name" value="{attr(name)}" size="30">',
        f'  <select name="show">{shows}</select>',
        '  <input type="submit" name="kl_style_store.filter_channels()" value="Filter">',
        '</form>',
        f'<p>{matched} of {total} channels'
        + (f'; the first {PAGE_MAX_ROWS} are shown, narrow the filter' if matched > len(rows) else '')
        + '.</p>',
        # a form cannot be in a table row; a form as a CSS table row instead
        '<div class="table">',
        '<div class="row head"><span>cid</span><span>name</span><span>type</span>'
        '<span>last value</span><span>ts</span><span>inserted_at</span>'
        '<span>unit</span><span>description</span><span></span><span></span></div>',
    ]
    for r in rows:
        valid_from = f'<br><span class="dim small">from {attr(r["valid_from"])}</span>' if r['valid_from'] else ''
        plot = ''
        if r['type'] in ('double', 'integer', 'boolean') and r['last_epoch'] is not None:
            # the last day; up to the last value if the channel has stopped
            href = f'./slowplot.html?channel={urllib.parse.quote(r["name"])}&length=86400&grid=1x1'
            href += f'&to={int(r["last_epoch"]) + 60}&reload=0' if r['stopped'] else '&reload=60'
            plot = f'<a class="button" href="{attr(href)}" target="_blank">Plot</a>'
        lines += [
            '<form class="row">',
            f'<span class="num">{r["cid"]}<input type="hidden" name="cid" value="{r["cid"]}"></span>',
            f'<span>{attr(r["name"])}{valid_from}</span><span>{r["type"]}</span>',
            f'<span>{attr(r["last_value"])}</span>',
            f'<span class="dim">{attr(r["last_ts"])}</span><span class="dim">{attr(r["last_inserted_at"])}</span>',
            f'<span><input name="unit" value="{attr(r["unit"])}"{unfilled(r["unit"])} size="8"></span>',
            f'<span><input name="description" value="{attr(r["description"])}"{unfilled(r["description"])} size="40"></span>',
            '<span><input type="submit" name="kl_style_store.describe_channel()" value="Set"></span>',
            f'<span>{plot}</span>',
            '</form>',
        ]
    lines += [
        '</div>',
        '</div>',
    ]
    return '\n'.join(lines)


@tasklet.finalize()
async def finalize():
    if pool is not None:
        await pool.close()


if __name__ == '__main__':
    tasklet.run(mesh_url='slowmq://localhost:18881')
