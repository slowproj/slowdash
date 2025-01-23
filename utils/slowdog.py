#! /usr/bin/env python3

'''slowdog.py: SlowDash watchdog
periodically sends a HTTP request and if timeout or an error occurs, terminate the slowdash process and restart it
'''


startup_grace = 300
terminate_grace = 30
check_interval = 300
timeout = 300


import sys, time, signal, subprocess

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

    
import urllib.request
def is_alive():
    url = f'http://localhost:{port}/api/ping'
    status = None
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=timeout) as response:
            status = response.status
    except Exception as e:
        return False
    return status == 200

    

is_stop_requested = False
def handle_signal(signum, frame):
    global is_stop_requested
    is_stop_requested = True
    sys.stderr.write(f'SlowDog: Signal {signum} handled\n')
signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)


while not is_stop_requested:
    proc = subprocess.Popen(cmd, shell=False)
    if port is None:
        proc.wait()
        break
    sys.stderr.write(f'SlowDog: starting {cmd}\n')
    
    last_check = time.time() + startup_grace
    while not is_stop_requested and proc.poll() is None:
        time.sleep(0.1)
        if time.time() - last_check < check_interval:
            continue
        
        last_check = time.time()
        if not is_alive():
            sys.stderr.write(f'SlowDog: no response from {name}\n')
            break
        
    if proc.poll() is None:
        sys.stderr.write(f'SlowDog: terminating {name}\n')
        proc.terminate()
        proc.send_signal(signal.SIGINT)
        term_time = time.time()
        while proc.poll() is None:
            time.sleep(0.1)
            if time.time() - term_time > terminate_grace:
                sys.stderr.write(f'SlowDog: killing {name}\n')
                proc.kill()
                break
        
    proc.wait()
    sys.stderr.write(f'SlowDog: {name} is terminated\n')

