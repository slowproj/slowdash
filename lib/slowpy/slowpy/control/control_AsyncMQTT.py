# Created by Sanshiro Enomoto on 13 March 2026 #

import asyncio, time
from slowpy.control import ControlNode, ControlException

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class MQTTNode(ControlNode):
    def __init__(self, host:str, port:int=1883):
        self.host = host
        self.port = port
        self.keepalive = 60
        
        self.subscribers: dict[str,list[SubscribeNode]] = {}
        self.receiver_task = None

        self.client = None
        self.connected = False
        self.disconnected = False
        self.connect_lock = asyncio.Lock()
        self.subscribe_lock = asyncio.Lock()
        self.retry_wait = 10
        self.last_connect_attempt_time = 0
        
        
    def __del__(self):
        if self.receiver_task is not None:
            self.receiver_task.cancel()
        if self.client:
            del self.client


    async def aio_close(self):
        if self.client is None:
            return

        if self.receiver_task is not None:
            try:
                self.receiver_task.cancel()
            except:
                pass
            self.receiver_task = None

        if self.connected:
            try:
                await self.client.__aexit__(None, None, None)
                logger.info(f'MQTT Connection Closed')
            except:
                pass
            self.connected = False
            
        del self.client
        self.client = None

        
    def publish(self, topic):
        return PublishNode(self, topic)


    def subscribe(self, topic_filter, handler=None, timeout=None):
        return SubscribeNode(self, topic_filter, handler, timeout)

     
    async def aio_do_connect(self):
        async with self.connect_lock:
            if self.connected:
                return True

            now = time.monotonic()
            if now - self.last_connect_attempt_time < self.retry_wait:
                return False
            self.last_connect_attempt_time = now

            if self.receiver_task is not None:
                try:
                    self.receiver_task.cancel()
                except:
                    pass

            if self.client is None:
                try:
                    import aiomqtt
                    self.client = aiomqtt.Client(self.host, self.port, keepalive=self.keepalive)
                except Exception as e:
                    logging.error(f'MQTT: {e}')
                    self.client = None
                    return False
            
            try:
                await self.client.__aenter__()
            except Exception as e:
                logger.error(f'Unable to connect to MQTT broker: {e}')
                return False
            else:
                logger.info(f'MQTT broker connected')
            
            self.connected = True
        
            if self.disconnected:
                logger.info(f'MQTT: reconnected')
                self.disconnected = False
                for topic_filter in self.subscribers:
                    await self.client.subscribe(topic_filter)
                                
            async def receiver():
                try:
                    async for msg in self.client.messages:
                        logger.debug(f'MQTT message: ({str(msg.topic)}) {msg.payload.decode()}')
                        for topic_filter, subscribers in self.subscribers.items():
                            if not msg.topic.matches(topic_filter):
                                continue
                            logger.debug(f'MQTT message topic matches: {msg.topic} ~ {topic_filter}')
                            for subscriber in subscribers:
                                await subscriber.aio_do_handle_message(msg)
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logging.warning(f'MQTT: error: {e}')
                    self.disconnected = True
                    await self.aio_close() # this will cause retries
                    await asyncio.sleep(self.retry_wait)

            self.receiver_task = asyncio.create_task(receiver())

            return True
    
        
    async def aio_do_subscribe(self, topic_filter, subscribe_node):
        async with self.subscribe_lock:
            if not await self.aio_do_connect():
                return False
        
            if topic_filter not in self.subscribers:
                logger.debug(f'MQTT subscribe: {topic_filter}')
                await self.client.subscribe(topic_filter)
                self.subscribers[topic_filter] = []
            
            self.subscribers[topic_filter].append(subscribe_node)

            return True
        
     
    @classmethod
    def _node_creator_method(cls):
        def async_mqtt(self, host:str, port:int=1883):
            if True:
                return MQTTNode(host, port)
            
            name = '%s:%s' % (host, str(port))
            try:
                self._mqtt_nodes.keys()
            except:
                self._mqtt_nodes = {}
            node = self._mqtt_nodes.get(name, None)
        
            if node is None:
                node = MQTTNode(host, port)
                self._mqtt_nodes[name] = node

            return node

        return async_mqtt

    
    
class PublishNode(ControlNode):
    def __init__(self, mqtt, topic):
        self.mqtt = mqtt
        self.topic = topic

        
    async def aio_set(self, value):
        if not await self.mqtt.aio_do_connect():
            return None

        try:
            await self.mqtt.client.publish(self.topic, value)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logging.warning(f'MQTT: error: {e}')
            self.disconnected = True
            await self.aio_close() # this will cause retries
            await asyncio.sleep(self.retry_wait)

        
class SubscribeNode(ControlNode):
    def __init__(self, mqtt:MQTTNode, topic_filter:str, handler=None, timeout=None):
        """
        - If handler is not None, it is called on receiving a message.
        - Otherwise, the received messages are queued, which can be retrieved by has_data()/get()
        """

        self.mqtt = mqtt
        self.topic_filter = topic_filter
        self.timeout = timeout
        
        self.queue = asyncio.Queue(maxsize=1024)
        
        async def default_handler(message):
            await self.queue.put(message)
        self.handler = handler or default_handler
        
        self.registered = False
        self.register_lock = asyncio.Lock()

        
    async def aio_do_handle_message(self, message):
        result = self.handler(message)
        if asyncio.iscoroutine(result):
            await result


    async def aio_has_data(self):
        async with self.register_lock:
            if not self.registered:
                if not await self.mqtt.aio_do_subscribe(self.topic_filter, self):
                    return False
                else:
                    self.registered = True
            
        return not await self.queue.empty()

        
    async def aio_get(self):
        """
        return aiomqtt.Message (or None), which has the following fields:
          - topic: aiomqtt.client.Topic (which has __str__())
          - payload: bytes
          - qos: int
          - retain: bool
          - mid: int
          - properties: paho.mqtt.properties.Properties|None
        """
        async with self.register_lock:
            if not self.registered:
                if not await self.mqtt.aio_do_subscribe(self.topic_filter, self):
                    return None
                else:
                    self.registered = True

        try:
            if self.timeout is None:
                return await self.queue.get()
            elif self.timeout <= 0:
                return await self.queue.get_nowait()
            else:
                return await asyncio.wait_for(self.queue.get(), timeout=self.timeout)
        except (asyncio.CancelledError, asyncio.TimeoutError, asyncio.QueueEmpty):
            return None

        
    ## child nodes ##
    # mqtt.subscribe(topic_pettern).payload()
    def payload(self):
        return SubscribePayloadNode(self)
        

    
class SubscribePayloadNode(ControlNode):
    def __init__(self, subscribe_node):
        self.subscribe_node = subscribe_node
        

    async def aio_get(self):
        msg = await self.subscribe_node.aio_get()
        if msg is None:
            return None
        else:
            return msg.payload
