#!/usr/bin/env python3
# Daily administration of kl_pg_store: channel list, unit and description,
# rejections. For everything else, use SQL.
#
#   export KL_ADMIN_DB=postgresql://kl_admin:PASSWORD@localhost:15432/kldb
#   python3 kl_admin.py list env.                     # channels whose name contains "env."
#   python3 kl_admin.py list --unfilled               # without unit or description
#   python3 kl_admin.py describe env.lab.temp --unit degC --description 'Lab temperature'
#   python3 kl_admin.py export --unfilled > channels.csv
#   (edit channels.csv)
#   python3 kl_admin.py import channels.csv           # shows the changes; --yes to apply
#   python3 kl_admin.py create env.lab.pressure --type double --unit hPa
#   python3 kl_admin.py rejections --since '1 day'
#
# The DB is given by --dsn, or KL_ADMIN_DB, or KL_WRITER_DB. create and
# import --create need the writer role (or admin); the others work also with
# the monitor role.
#
# Values are written as given: an empty cell is '' (e.g. no unit), never NULL
# (not described yet, as created automatically). NULL is exported as an empty
# cell; import skips the rows that are the same as exported, and writes the
# other rows as they are.

import argparse
import asyncio
import csv
import os
import sys

import asyncpg


async def connect(args):
    dsn = args.dsn or os.environ.get('KL_ADMIN_DB') or os.environ.get('KL_WRITER_DB')
    if dsn is None:
        sys.exit('kl_admin: no DB: give --dsn, or set KL_ADMIN_DB')
    try:
        return await asyncpg.connect(dsn, server_settings={ 'search_path': args.schema, 'timezone': 'UTC' })
    except Exception as e:
        sys.exit(f'kl_admin: cannot connect to the DB: {e}')


# the current (latest valid_from) channel of each name, with the latest value
CHANNELS_SQL = '''
SELECT DISTINCT ON (c.name)
  c.cid, c.name, c.type, c.unit, c.description,
  left(COALESCE(l.value::text, l.value_int::text, l.value_bool::text, l.value_text, l.value_jsonb::text), 20) AS last_value,
  to_char(l.ts, 'YYYY-MM-DD HH24:MI:SS') AS last_ts
FROM channels c LEFT JOIN raw_latest l USING (cid)
WHERE strpos(c.name, $1) > 0
  AND (NOT $2 OR c.unit IS NULL OR c.description IS NULL)
ORDER BY c.name, c.valid_from DESC
'''


def print_table(header, rows):
    rows = [ [ '' if x is None else str(x) for x in row ] for row in rows ]
    widths = [ max([ len(h) ] + [ len(row[i]) for row in rows ]) for i, h in enumerate(header) ]
    print('  '.join(h.ljust(w) for h, w in zip(header, widths)).rstrip())
    for row in rows:
        print('  '.join(x.ljust(w) for x, w in zip(row, widths)).rstrip())


async def cmd_list(conn, args):
    rows = await conn.fetch(CHANNELS_SQL, args.pattern, args.unfilled)
    print_table(
        [ 'cid', 'name', 'type', 'unit', 'description', 'last value', 'last ts (UTC)' ],
        [ (r['cid'], r['name'], r['type'], r['unit'], r['description'], r['last_value'], r['last_ts']) for r in rows ]
    )
    print(f'({len(rows)} channels)', file=sys.stderr)


async def cmd_describe(conn, args):
    if args.channel.isdigit():
        current = await conn.fetchrow('SELECT cid, unit, description FROM channels WHERE cid = $1', int(args.channel))
    else:
        current = await conn.fetchrow('SELECT cid, unit, description FROM channels WHERE name = $1 ORDER BY valid_from DESC LIMIT 1', args.channel)
    if current is None:
        sys.exit(f'kl_admin: no channel: {args.channel}')
    # an option not given keeps the current value
    unit = current['unit'] if args.unit is None else args.unit
    description = current['description'] if args.description is None else args.description
    cid = await conn.fetchval('SELECT describe_channel($1::integer, $2::text, $3::text)', current['cid'], unit, description)
    row = await conn.fetchrow('SELECT cid, name, unit, description FROM channels WHERE cid = $1', cid)
    print_table([ 'cid', 'name', 'unit', 'description' ], [ tuple(row) ])


async def cmd_create(conn, args):
    cid = await conn.fetchval('SELECT create_channel($1::text, $2::text, $3::text, $4::text)', args.name, args.type, args.unit, args.description)
    print(f'{args.name}: cid {cid}')


async def cmd_export(conn, args):
    rows = await conn.fetch(CHANNELS_SQL, args.pattern, args.unfilled)
    writer = csv.writer(sys.stdout)
    writer.writerow([ 'name', 'type', 'unit', 'description' ])
    for r in rows:
        writer.writerow([ r['name'], r['type'], r['unit'], r['description'] ])


async def cmd_import(conn, args):
    with open(args.csv_file, newline='') as f:
        entries = list(csv.DictReader(f))
    current = { r['name']: r for r in await conn.fetch(CHANNELS_SQL, '', False) }

    changes, creates = [], []
    for e in entries:
        name = (e.get('name') or '').strip()
        if not name:
            continue
        unit = (e.get('unit') or '').strip()
        description = (e.get('description') or '').strip()
        c = current.get(name)
        if c is None:
            if args.create:
                creates.append((name, (e.get('type') or '').strip() or 'double', unit, description))
            else:
                print(f'unknown channel (skipped; --create to create): {name}', file=sys.stderr)
            continue
        # the same as exported (NULL as an empty cell): not touched
        if (unit, description) == (c['unit'] or '', c['description'] or ''):
            continue
        changes.append((c['cid'], name, c['unit'], unit, c['description'], description))

    for cid, name, old_unit, new_unit, old_description, new_description in changes:
        print(f'{name} (cid {cid})')
        if old_unit != new_unit:
            print(f'    unit:        {old_unit!r} -> {new_unit!r}')
        if old_description != new_description:
            print(f'    description: {old_description!r} -> {new_description!r}')
    for name, type, unit, description in creates:
        print(f'{name} (new, {type}): unit {unit!r}, description {description!r}')
    if len(changes) + len(creates) == 0:
        print('no changes')
        return
    if not args.yes:
        print(f'{len(changes)} to change, {len(creates)} to create; run with --yes to apply')
        return

    async with conn.transaction():
        for cid, name, old_unit, new_unit, old_description, new_description in changes:
            await conn.execute('SELECT describe_channel($1::integer, $2::text, $3::text)', cid, new_unit, new_description)
        for name, type, unit, description in creates:
            await conn.execute('SELECT create_channel($1::text, $2::text, $3::text, $4::text)', name, type, unit, description)
    print(f'{len(changes)} changed, {len(creates)} created')


async def cmd_rejections(conn, args):
    rows = await conn.fetch('''
        SELECT status, record->>'name' AS name, count(*) AS count, max(received_at) AS last, max(detail) AS detail
        FROM rejections WHERE received_at > now() - $1::text::interval
        GROUP BY 1, 2 ORDER BY 3 DESC
    ''', args.since)
    print_table(
        [ 'status', 'name', 'count', 'last received (UTC)', 'detail' ],
        [ (r['status'], r['name'], r['count'], r['last'].strftime('%Y-%m-%d %H:%M:%S'), (r['detail'] or '')[:60]) for r in rows ]
    )


async def main(args):
    conn = await connect(args)
    try:
        await args.func(conn, args)
    except asyncpg.PostgresError as e:
        sys.exit(f'kl_admin: {e}')
    finally:
        await conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='kl_pg_store administration (see README_ja.md)')
    parser.add_argument('--dsn', help='PostgreSQL URL (default: $KL_ADMIN_DB, $KL_WRITER_DB)')
    parser.add_argument('--schema', default='kl_store')
    sub = parser.add_subparsers(required=True)

    p = sub.add_parser('list', help='list channels')
    p.add_argument('pattern', nargs='?', default='', help='part of the name')
    p.add_argument('--unfilled', action='store_true', help='only without unit or description')
    p.set_defaults(func=cmd_list)

    p = sub.add_parser('describe', help='set unit and/or description')
    p.add_argument('channel', help='name (the current channel) or cid')
    p.add_argument('--unit', help='"" for no unit; not given: unchanged')
    p.add_argument('--description', help='not given: unchanged')
    p.set_defaults(func=cmd_describe)

    p = sub.add_parser('create', help='create a channel')
    p.add_argument('name')
    p.add_argument('--type', default='double', choices=[ 'double', 'integer', 'boolean', 'text', 'json' ])
    p.add_argument('--unit')
    p.add_argument('--description')
    p.set_defaults(func=cmd_create)

    p = sub.add_parser('export', help='write channels as CSV to stdout')
    p.add_argument('pattern', nargs='?', default='', help='part of the name')
    p.add_argument('--unfilled', action='store_true', help='only without unit or description')
    p.set_defaults(func=cmd_export)

    p = sub.add_parser('import', help='write unit and description of the changed rows of CSV')
    p.add_argument('csv_file')
    p.add_argument('--yes', action='store_true', help='apply the changes (default: only show them)')
    p.add_argument('--create', action='store_true', help='create unknown channels (type from the CSV, default double)')
    p.set_defaults(func=cmd_import)

    p = sub.add_parser('rejections', help='summary of the recent rejections')
    p.add_argument('--since', default='1 day', help='interval (default: "1 day")')
    p.set_defaults(func=cmd_rejections)

    args = parser.parse_args()
    asyncio.run(main(args))
