#! /usr/bin/env python3        


import sys, os, time
import slowpy as slp

import signal, threading
current_thread = None
stop_requested = False

import logging
logger = logging.getLogger('TestDataGenerator')
logger.addHandler(logging.StreamHandler(sys.stderr))
logger.setLevel(logging.INFO)


def run(params):
    datastore = slp.DataStore_SQLite('SlowStore')
    dummy_device = slp.DummyWalkDevice(n=4)

    while not stop_requested:
        time.sleep(1)
        for record in dummy_device.read():
            datastore.write_timeseries(record['value'], tag='ch%02d'%record['channel'], timestamp=record['time'])
    


def start(params):
    global current_thread
    if current_thread is None:
        current_thread = threading.Thread(target=run, args=(params,))
        current_thread.start()

    
def stop(signum=None, frame=None):
    global current_thread, stop_requested
    if current_thread is not None:
        stop_requested = True
        logger.info('stop requested. Wait a second...')
        current_thread.join()
        current_thread = None
        logger.info('stop completed.')

        
def initialize(params):
    start(params)

    
def finalize():
    stop()
    


if __name__ == '__main__':
    signal.signal(signal.SIGINT, stop)
    start({})
