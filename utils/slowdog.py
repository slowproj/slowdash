#! /usr/bin/env python3

startup_grace = 60
terminate_grace = 5
check_interval = 10


import sys, time, getopt, signal, subprocess

if len(sys.argv) < 2:
    print(f'USAGE: {sys.argv[0]} slowdash_bin_path args...')
    sys.exit(0)
    
cmd = [sys.executable] + sys.argv[1:]
name = sys.argv[1]

port = None
for arg in sys.argv[2:]:
    if arg.startswith('--port='):
        port = arg[7:]
        break

    

import requests

def is_alive():
    response = requests.get(f'http://localhost:{port}/ping')
    return response.status_code == 200

    

is_stop_requested = False
def handle_signal(signum, frame):
    global is_stop_requested
    is_stop_requested = True
    print(f'SlowDog: Signal {signum} handled')
signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)


while not is_stop_requested:
    proc = subprocess.Popen(cmd, shell=False)
    if port is None:
        proc.wait()
        break
    print(f'SlowDog: starting {cmd}')
    
    last_check = time.time() + startup_grace
    while not is_stop_requested and proc.poll() is None:
        time.sleep(0.1)
        if time.time() - last_check < check_interval:
            continue
        
        last_check = time.time()
        if not is_alive():
            print(f'SlowDog: no response from {name}')
            break
        
    if proc.poll() is None:
        print(f'SlowDog: terminating {name}')
        proc.terminate()
        proc.send_signal(signal.SIGINT)
        term_time = time.time()
        while proc.poll() is None:
            time.sleep(0.1)
            if time.time() - term_time > terminate_grace:
                print(f'SlowDog: killing {name}')
                proc.kill()
                break
        
    proc.wait()
    print(f'SlowDog: {name} is terminated')

