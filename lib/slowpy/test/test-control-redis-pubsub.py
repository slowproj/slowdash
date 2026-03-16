import sys, time

from slowpy.control import control_system as ctrl
redis = ctrl.import_control_module('Redis').redis('redis://localhost:6379/12')


def send(message):
    pub = redis.publish('message:all')
    while True:
        try:
            pub.set(message)
            time.sleep(1)
        except KeyboardInterrupt:
            break


def receive():
    sub = redis.subscribe('message:*')
    while True:
        try:
            message = sub.data().get()
            if message is not None:
                print(message)
            else:
                time.sleep(0.1)
        except KeyboardInterrupt:
            break
        


if __name__ == '__main__':
    if len(sys.argv) > 1:
        send(sys.argv[1])
    else:
        receive()
