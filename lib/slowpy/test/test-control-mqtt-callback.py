
print('MQTT Chat')
print('type ctrl-d to stop')


from slowpy.control import control_system as ctrl
mqtt = ctrl.import_control_module('MQTT').mqtt('localhost')

def handler(message):
    print(message.payload.decode())
mqtt.subscriber('chat/#', handler)
        
while True:
    try:
        line = input()
    except (EOFError, KeyboardInterrupt):
        break
    mqtt.publisher('chat/all').set(line)

mqtt.close()
