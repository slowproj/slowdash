
print('MQTT Chat')
print('type ctrl-d to stop')


from slowpy.control import control_system as ctrl
mqtt = ctrl.import_control_module('MQTT').mqtt('localhost')

is_running = True

sub = mqtt.subscriber('chat/#', timeout=0.1)
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
    mqtt.publisher('chat/all').set(({'sender':'me'}, line))


th.join()
mqtt.close()

