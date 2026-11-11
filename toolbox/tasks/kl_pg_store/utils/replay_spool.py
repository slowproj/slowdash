#!/usr/bin/env python3
# Writes the messages spooled by slowtask-kl_pg_store.py into the DB.
#
#   python3 replay_spool.py postgresql://kl_writer:PASSWORD@localhost:15432/kldb kl_pg_store-spool.jsonl
#
# The spool file is first renamed, so the slowtask can keep spooling while
# this runs. Lines that still fail are appended back to the spool file.
# Files left by an interrupted run (<spool>.replaying-*) are replayed first.
# Replaying a line twice is harmless: the second time, the records are
# rejected as duplicate.

import argparse
import asyncio
import glob
import os
import sys
import time

import asyncpg


async def replay(dsn, spool, schema):
    files = sorted(glob.glob(glob.escape(spool) + '.replaying-*'))
    if os.path.exists(spool):
        replaying = f'{spool}.replaying-{time.time_ns()}'
        os.rename(spool, replaying)
        files.append(replaying)
    if len(files) == 0:
        print(f'{spool}: no spool file')
        return 0

    schema = '"%s"' % schema.replace('"', '""')
    insert_sql = f'SELECT input_index, status, cid, detail FROM {schema}.insert_records($1::jsonb)'
    n_lines, n_failed, n_rejected = 0, 0, 0

    conn = await asyncpg.connect(dsn)
    try:
        for replaying in files:
            with open(replaying) as f:
                for line in f:
                    line = line.strip()
                    if len(line) == 0:
                        continue
                    n_lines += 1
                    try:
                        rejected = await conn.fetch(insert_sql, line)
                        n_rejected += len(rejected)
                    except Exception as e:
                        print(f'{replaying}: {e}', file=sys.stderr)
                        n_failed += 1
                        with open(spool, 'a') as out:
                            out.write(line + '\n')
            os.remove(replaying)
    finally:
        await conn.close()
    print(f'{n_lines} messages replayed; {n_failed} failed (back to {spool}); {n_rejected} records rejected (see the rejections table)')
    return 1 if n_failed > 0 else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Replay the kl_pg_store spool file')
    parser.add_argument('dsn', help='PostgreSQL URL of the writer role')
    parser.add_argument('spool', help='spool file (JSON Lines)')
    parser.add_argument('--schema', default='kl_store')
    args = parser.parse_args()
    sys.exit(asyncio.run(replay(args.dsn, args.spool, args.schema)))
