import sys, time

from slowpy.control import control_system as ctrl
redis = ctrl.import_control_module('Redis').redis('redis://localhost:6379/12')


is_running = True

sub = redis.subscriber('chat:*', timeout=0.1)
def receiver():
    while is_running:
        headers, data = sub.json().get()
        if data is not None:
            print(f'{headers}: {data}')
            
import threading
th = threading.Thread(target=receiver)
th.start()

        
while is_running:
    try:
        line = input()
    except (EOFError, KeyboardInterrupt):
        is_running = False
        break
    redis.publisher('chat:all').json({'sender':'me'}).set({'message':line})


th.join()
redis.close()

