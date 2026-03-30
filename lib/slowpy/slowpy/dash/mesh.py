# Created by Sanshiro Enomoto on 23 March 2026 #

import asyncio, inspect, logging
from urllib.parse import urlsplit
from slowpy.control import control_system as ctrl


class Mesh:
    def __init__(self, url=None, *, timeout:float=0.1, sep='.', single_wc='*', tail_wc='>'):
        self.pubargs = {}
        self.subargs = { 'timeout': timeout }

        self.sep = sep
        self.single_wc = single_wc
        self.tail_wc = tail_wc
        
        self.sep_mesh = sep
        self.single_wc_mesh = single_wc
        self.tail_wc_mesh = tail_wc
        
        if url is not None:
            self.connect(url)
        else:
            self.pubsub = ctrl.import_control_module('AsyncLocalPubsub').async_localpubsub()

        
    def connect(self, url:str):
        if url is None:
            return
        
        try:
            o = urlsplit(url)
            if o.scheme in ['slowmq', 'slowdash']:
                self.pubsub = ctrl.import_control_module('AsyncSlowMQ').async_slowmq(f'slowmq://{o.netloc}')
                self.sep_mesh, self.single_wc_mesh, self.tail_wc_mesh = tail_wc = '.', '*', '>'
            elif o.scheme == 'nats':
                self.pubsub = ctrl.import_control_module('AsyncNATS').async_nats(url)
                self.sep_mesh, self.single_wc_mesh, self.tail_wc_mesh = tail_wc = '.', '*', '>'
            elif o.scheme == 'mqtt':
                self.pubsub = ctrl.import_control_module('AsyncMQTT').async_mqtt(o.hostname, o.port or 1883)
                self.sep_mesh, self.single_wc_mesh, self.tail_wc_mesh = tail_wc = '/', '+', '#'
            elif o.scheme == 'redis':
                self.pubsub = ctrl.import_control_module('AsyncRedis').async_redis(url)
                self.sep_mesh, self.single_wc_mesh, self.tail_wc_mesh = tail_wc = ':', '*', '*'
            elif o.scheme in ['amqp', 'rabbitmq', 'rmq']:
                amqp = ctrl.import_control_module('AsyncRabbitMQ').async_rabbitmq(f'amqp://{o.netloc}')
                if len(o.path) > 1:
                    self.pubsub = amqp.topic_exchange(o.path[1:])
                else:
                    logging.error('Mesh: AMQP (RabbitMQ) requries an exchange name')
                self.sep_mesh, self.single_wc_mesh, self.tail_wc_mesh = tail_wc = '.', '*', '#'
            else:
                logging.error('Mesh: unknown pubsub type: %s' % scheme)
        except Exception as e:
            logging.error(e)

            
    def _convert_topic(self, topic:str):
        converted = topic
        
        if self.sep is not None and self.sep != self.sep_mesh:
            if topic.count(self.sep_mesh):
                logging.warning(f'Mesh: Separator char "{self.sep_mesh}" is used in topic "{topic}"')
            converted = converted.replace(self.sep, self.sep_mesh)
            
        if self.single_wc is not None and self.single_wc != self.single_wc_mesh:
            converted = converted.replace(self.single_wc, self.single_wc_mesh)
            if topic.count(self.single_wc_mesh):
                logging.warning(f'Mesh: Wildcard char "{self.single_wc_mesh}" is used in topic "{topic}"')
            
        if self.tail_wc is not None and self.tail_wc != self.tail_wc_mesh:
            converted = converted.replace(self.tail_wc, self.tail_wc_mesh)
            if topic.count(self.tail_wc_mesh):
                logging.warning(f'Mesh: Wildcard char "{self.tail_wc_mesh}" is used in topic "{topic}"')

        return converted

            
    async def aio_close(self):
        try:
            await self.pubsub.aio_close()
        except:
            pass
            
            
    def publisher(self, topic:str):
        return self.pubsub.publisher(self._convert_topic(topic), **self.pubargs).json()


    def subscriber(self, topic:str):
        return self.pubsub.subscriber(self._convert_topic(topic), **self.subargs).json()


    async def aio_publish(self, topic:str, value, *, headers:dict|None=None):
        return await self.publisher(topic).headers(headers or {}).aio_set(value)


    def publish(self, topic:str, value, *, headers:dict|None=None):
        loop = asyncio.get_running_loop()
        loop.create_task(self.aio_publish(topic, value, headers=headers))
