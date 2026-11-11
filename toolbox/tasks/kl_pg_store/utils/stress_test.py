#!/usr/bin/env python3
# Writes dummy records through insert_records(), and reports the rate and
# the latency of the calls. Use a test DB: the channels (<prefix>NNNN) and
# records are never deleted.
#
#   python3 stress_test.py postgresql://kl_writer:writer@localhost:15432/kldb
#   python3 stress_test.py DSN --rate 0 --connections 4    # as fast as possible
#
# Each call writes --channels-per-call records (one per channel, rotating over
# --channels channels) with the current time, like one DataPacket message.

import argparse
import asyncio
import json
import random
import statistics
import time

import asyncpg


async def writer(pool, sql, args, names, counter, latencies, rejected, interval, stop_at):
    next_time = time.monotonic()
    while time.monotonic() < stop_at:
        k = counter[0]
        counter[0] += 1
        records = [
            { 'name': names[(k * args.channels_per_call + i) % len(names)], 'ts': time.time(), 'value': random.gauss(20, 1) }
            for i in range(args.channels_per_call)
        ]
        start = time.monotonic()
        rows = await pool.fetch(sql, json.dumps(records))
        latencies.append(time.monotonic() - start)
        rejected[0] += len(rows)
        if interval > 0:
            next_time += interval
            await asyncio.sleep(max(0, next_time - time.monotonic()))


async def main(args):
    schema = '"%s"' % args.schema.replace('"', '""')
    sql = f'SELECT input_index, status FROM {schema}.insert_records($1::jsonb)'
    names = [ f'{args.prefix}{i:04d}' for i in range(args.channels) ]
    pool = await asyncpg.create_pool(dsn=args.dsn, min_size=args.connections, max_size=args.connections)

    # each connection takes its share of the rate
    interval = args.connections / args.rate if args.rate > 0 else 0
    counter, latencies, rejected = [0], [], [0]
    start = time.monotonic()
    stop_at = start + args.duration
    await asyncio.gather(*[
        writer(pool, sql, args, names, counter, latencies, rejected, interval, stop_at)
        for i in range(args.connections)
    ])
    elapsed = time.monotonic() - start
    await pool.close()

    latencies.sort()
    def percentile(p):
        return latencies[min(len(latencies) - 1, int(len(latencies) * p))] * 1000
    rows = len(latencies) * args.channels_per_call
    print(f'calls: {len(latencies)}, records: {rows}, rejected: {rejected[0]}, in {elapsed:.1f} s')
    print(f'rate: {len(latencies) / elapsed:.1f} calls/s, {rows / elapsed:.0f} records/s')
    print(f'latency [ms]: median {statistics.median(latencies) * 1000:.2f}, '
          f'p99 {percentile(0.99):.2f}, max {latencies[-1] * 1000:.2f}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('dsn', help='PostgreSQL URL of the writer role')
    parser.add_argument('--schema', default='kl_store')
    parser.add_argument('--prefix', default='stress.test.ch', help='channel name prefix')
    parser.add_argument('--channels', type=int, default=1000)
    parser.add_argument('--channels-per-call', type=int, default=10)
    parser.add_argument('--rate', type=float, default=10, help='calls/s in total; 0 for as fast as possible')
    parser.add_argument('--connections', type=int, default=1)
    parser.add_argument('--duration', type=float, default=60, help='seconds')
    asyncio.run(main(parser.parse_args()))
