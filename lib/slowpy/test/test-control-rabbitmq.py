
print('RabbitMQ Chat')
print('type ctrl-d to stop')


from slowpy.control import control_system as ctrl
rabbitmq = ctrl.import_control_module('RabbitMQ').rabbitmq('amqp://slowdash:slowdash@localhost')
exchange = rabbitmq.topic_exchange('slowchat')


is_running = True

sub = exchange.subscriber('chat.*', timeout=0.1)
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
    exchange.publisher('chat.all').set(line)


th.join()
rabbitmq.close()
