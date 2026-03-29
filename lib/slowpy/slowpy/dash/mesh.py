# Created by Sanshiro Enomoto on 23 March 2026 #

import asyncio, inspect
from urllib.parse import urlsplit
from slowpy.control import control_system as ctrl

import logging


class EmptyPubsubNode:
    def __init__(self):
        pass
    
    def aio_open():
        pass

    def aio_close():
        pass

    def publisher(self, topic, **kwargs):
        return EmptyPublisherNode(topic)

    def subscriber(self, topic_filter, timeout=None, **kwargs):
        return EmptySubscriberNode(topic_filter, timeout=timeout)

    
class EmptyPublisherNode:
    def __init__(self, topic):
        self.topic = topic

    async def aio_set(self, value):
        print(f'PUBSLIH ({self.topic}): {repr(value)}')

    def json(self, headers=None):
        return EmptyPublisherJsonNode(self)

    
class EmptySubscriberNode:
    def __init__(self, topic_filter:str, timeout=None):
        self.topic_filter = topic_filter
        self.timeout = timeout
        
    async def aio_get(self):
        if self.timeout is not None and self.timeout > 0:
            await asyncio.sleep(self.timeout)
        return None, None
    
    def json(self):
        return EmptySubscriberJsonNode(self)
        
    
class EmptyPublisherJsonNode:
    def __init__(self, publisher_node):
        self.publisher_node = publisher_node

    async def aio_set(self, value):
        return await self.publisher_node.aio_set(value)


class EmptySubscriberJsonNode:
    def __init__(self, subscriber_node):
        self.subscriber_node = subscriber_node

    async def aio_get(self):
        return await self.subscriber_node.aio_get()



class Mesh:
    def __init__(self, url=None, *, timeout:float=0.1):
        self.pubargs = {}
        self.subargs = { 'timeout': timeout }
        
        self.subscription_coros = []
        self.subscription_tasks = None

        if url is not None:
            self.connect(url)
        else:
            self.pubsub = EmptyPubsubNode()

        
    def connect(self, url:str):
        if url is None:
            return
        
        try:
            o = urlsplit(url)
            if o.scheme in ['slowmq', 'slowdash']:
                self.pubsub = ctrl.import_control_module('AsyncSlowMQ').async_slowmq(f'slowmq://{o.netloc}')
            elif o.scheme == 'nats':
                self.pubsub = ctrl.import_control_module('AsyncNATS').async_nats(url)
            elif o.scheme == 'mqtt':
                self.pubsub = ctrl.import_control_module('AsyncMQTT').async_mqtt(o.hostname, o.port or 1883)
            elif o.scheme == 'redis':
                self.pubsub = ctrl.import_control_module('AsyncRedis').async_redis(url)
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
        await self.aio_stop()
        
        if self.pubsub is not None:
            try:
                await self.pubsub.aio_close()
            except:
                pass
            
            
    def publisher(self, topic:str):
        if self.pubsub is None:
            return None
        
        return self.pubsub.publisher(topic, **self.pubargs).json()


    def subscriber(self, topic:str):
        if self.pubsub is None:
            return None
        
        return self.pubsub.subscriber(topic, **self.subargs).json()


    async def aio_publish(self, topic:str, value):
        publisher = self.publisher(topic)
        if publisher is None:
            return None
        else:
            return await publisher.aio_set(value)


    def publish(self, topic:str, value):
        publisher = self.publisher(topic)
        if publisher is None:
            return None
        
        asyncio.get_running_loop().create_task(publisher.aio_set(value))


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


    async def aio_start(self):
        if self.subscription_tasks is not None:
            await self.aio_stop()

        self.subscription_tasks = set()
        for coro in self.subscription_coros:
            task = asyncio.create_task(coro)
            task.add_done_callback(self.subscription_tasks.discard)
            self.subscription_tasks.add(task)
            

    async def aio_stop(self):
        if self.subscription_tasks is None:
            return
            
        for task in self.subscription_tasks:
            task.cancel()
        try:
            await asyncio.gather(*self.subscription_tasks, return_exceptions=True)
        except:
            pass
        finally:
            self.subscription_tasks = None


    def on(self, topic:str):
        """decorator to make a message handler
        Args:
        - topic: path pattern to match
        """
        def wrapper(func):
            self.subscription_coros.append(self.aio_subscribe(topic, func))
            return func
        return wrapper
