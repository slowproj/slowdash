# Created by Sanshiro Enomoto on 23 March 2026 #

import asyncio, inspect
from urllib.parse import urlsplit
from slowpy.control import control_system as ctrl

import logging


class Mesh:
    def __init__(self, url:str, *, timeout:float=0.1):
        self.url = url
        self.pubsub = None
        self.pubargs = {}
        self.subargs = { 'timeout': timeout }
        
        self.subscription_coros = []
        
        try:
            o = urlsplit(self.url)
            if o.scheme in ['slowmq', 'slowdash']:
                self.pubsub = ctrl.import_control_module('AsyncSlowMQ').async_slowmq(f'slowmq://{o.netloc}')
            elif o.scheme == 'nats':
                self.pubsub = ctrl.import_control_module('AsyncNATS').async_nats(self.url)
            elif o.scheme == 'mqtt':
                self.pubsub = ctrl.import_control_module('AsyncMQTT').async_mqtt(o.hostname, o.port or 1883)
            elif o.scheme == 'redis':
                self.pubsub = ctrl.import_control_module('AsyncRedis').async_redis(self.url)
            elif o.scheme in ['amqp', 'rabbitmq', 'rmq']:
                amqp = ctrl.import_control_module('AsyncRabbitMQ').async_rabbitmq(f'amqp://{o.netloc}')
                if len(o.path) > 1:
                    self.pubsub = amqp.topic_exchange(o.path[1:])
                else:
                    logging.error('Mesh: AMQP (RabbitMQ) requries an exchange name')
            else:
                logging.error('Mesh: unknown pubsub type: %s' % scheme)
        except Exception as e:
            logging.error(e)
        

    async def aio_close(self):
        if self.pubsub is not None:
            try:
                await self.pubsub.aio_close()
            except:
                pass
            
            
    def publisher(self, topic:str):
        if self.pubsub is None:
            return None
        
        return self.pubsub.publish(topic, **self.pubargs).json()


    def subscriber(self, topic:str):
        if self.pubsub is None:
            return None
        
        return self.pubsub.subscribe(topic, **self.subargs).json()


    async def aio_publish(self, topic:str, value):
        publisher = self.publisher(topic)
        if publisher is None:
            return None
        else:
            return await publisher.aio_set(value)


    async def aio_subscribe(self, topic:str, func):
        subscriber = self.subscriber(topic)
        if subscriber is None:
            return None

        nargs = len(inspect.signature(func).parameters)
        if nargs > 2:
            logging.error(f'Invalid mesh message handler: wrong number of arguments')
            return None

        async def receiver():
            try:
                while True:
                    headers, data = await subscriber.aio_get()
                    if data is None:
                        continue
                    if nargs == 0:
                        result = func()
                    elif nargs == 1:
                        result = func(data)
                    elif nargs == 2:
                        result = func(headers, data)
                    if asyncio.iscoroutine(result):
                        await result
            except Exception as e:
                logging.error(f'Error in mesh message handler: {e}')
        
        return await receiver()


    def on(self, topic:str):
        """decorator to make a message handler
        Args:
        - topic: path pattern to match
        """
        def wrapper(func):
            self.subscription_coros.append(self.aio_subscribe(topic, func))
            return func
        return wrapper


    async def aio_start(self):
        await asyncio.gather(*self.subscription_coros)
