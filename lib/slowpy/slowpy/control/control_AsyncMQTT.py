# Created by Sanshiro Enomoto on 13 March 2026 #

import asyncio, time, json
from slowpy.control import ControlNode, ControlException

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class MQTTNode(ControlNode):
    def __init__(self, host:str, port:int=1883, *, use_v5=True, keep_alive=60):
        self.host = host
        self.port = port
        self.use_v5 = use_v5   # if False, v3.11 is used, and headers (properties) are not available
        self.keep_alive = keep_alive
        
        self.subscribers: dict[str,list["SubscriberNode"]] = {}
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


    async def aio_open(self):
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
                    import paho.mqtt.client as mqtt
                    if self.use_v5:
                        from paho.mqtt.properties import Properties
                        from paho.mqtt.packettypes import PacketTypes
                        self.client = aiomqtt.Client(
                            self.host, self.port, keepalive=self.keep_alive, protocol=mqtt.MQTTv5
                        )
                        def dict2props(value:dict):
                            props = Properties(PacketTypes.PUBLISH)
                            props.UserProperty = [ (k,v) for k,v in value.items() ]
                            return props
                        self.dict2props = dict2props
                    else:
                        self.client = aiomqtt.Client(
                            self.host, self.port, keepalive=self.keep_alive, protocol=mqtt.MQTTv311
                        )
                        def dict2props(value:dict):
                            return None
                        self.dict2props = dict2props
                except Exception as e:
                    logger.error(f'AsyncMQTT: {e}')
                    self.client = None
                    return False
            
            try:
                await self.client.__aenter__()
            except Exception as e:
                logger.error(f'AsyncMQTT: Unable to connect to MQTT broker: {e}')
                return False
            else:
                logger.info(f'AsyncMQTT: connected: mqtt://{self.host}:{self.port}')
            
            self.connected = True
        
            if self.disconnected:
                logger.info(f'AsyncMQTT: reconnected')
                self.disconnected = False
                for topic_filter in self.subscribers:
                    await self.client.subscribe(topic_filter)
                                
            async def receiver():
                try:
                    async for msg in self.client.messages:
                        logger.debug(f'AsyncMQTT message: ({str(msg.topic)}) {msg.payload.decode()}')
                        for topic_filter, subscribers in self.subscribers.items():
                            if not msg.topic.matches(topic_filter):
                                continue
                            logger.debug(f'AsyncMQTT message topic matches: {msg.topic} ~ {topic_filter}')
                            for subscriber in subscribers:
                                await subscriber._handle_message(msg)
                except Exception as e:
                    logger.warning(f'AsyncMQTT: receiver(): error: {e}')
                    self.disconnected = True
                    await self.aio_close() # this will cause retries
                    await asyncio.sleep(1)

            self.receiver_task = asyncio.create_task(receiver())

            return True
    
        
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
                logger.info(f'AsyncMQTT Connection Closed')
            except:
                pass
            self.connected = False
            
        del self.client
        self.client = None

        
    def publisher(self, topic):
        return PublisherNode(self, topic)


    def subscriber(self, topic_filter, handler=None, timeout=None):
        return SubscriberNode(self, topic_filter, handler, timeout)

     
    async def _subscribe(self, topic_filter, subscriber_node):
        async with self.subscribe_lock:
            if not await self.aio_open():
                return False
        
            if topic_filter not in self.subscribers:
                logger.debug(f'AsyncMQTT subscribe: {topic_filter}')
                await self.client.subscribe(topic_filter)
                self.subscribers[topic_filter] = []
            
            self.subscribers[topic_filter].append(subscriber_node)

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

    
    
class PublisherNode(ControlNode):
    def __init__(self, mqtt_node, topic):
        self.mqtt_node = mqtt_node
        self.topic = topic

        
    async def aio_set(self, value):
        if not await self.mqtt_node.aio_open():
            return None

        body, headers = (None, {})
        if type(value) is tuple:
            if len(value) == 1:
                (body,) = value
            elif len(value) == 2:
                headers, body = value
        else:
            body = value

        try:
            await self.mqtt_node.client.publish(self.topic, body, properties=self.mqtt_node.dict2props(headers))
        except Exception as e:
            logger.warning(f'AsyncMQTT: publisher().aio_set(): error: {e}')
            self.mqtt_node.disconnected = True
            await self.mqtt_node.aio_close() # this will cause retries

        
    ## child nodes ##
    # nats.publisher(subject).json()
    def json(self, headers=None):
        return PublisherJsonNode(self, headers)


    
class SubscriberNode(ControlNode):
    def __init__(self, mqtt_node:MQTTNode, topic_filter:str, handler=None, timeout=None):
        """
        - If handler is not None, it is called on receiving a message.
        - Otherwise, the received messages are queued, which can be retrieved by has_data()/get()
        """

        self.mqtt_node = mqtt_node
        self.topic_filter = topic_filter
        self.timeout = timeout
        
        self.queue = asyncio.Queue(maxsize=1024)
        
        async def default_handler(message):
            await self.queue.put(message)
        self.handler = handler or default_handler
        
        self.registered = False
        self.register_lock = asyncio.Lock()

        
    async def _handle_message(self, message):
        try:
            result = self.handler(message)
            if asyncio.iscoroutine(result):
                await result
        except Exception as e:
            logging.error('AsyncMQTT: error in message handler: {e}')


    async def aio_has_data(self):
        async with self.register_lock:
            if not self.registered:
                if not await self.mqtt_node._subscribe(self.topic_filter, self):
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
                if not await self.mqtt_node._subscribe(self.topic_filter, self):
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
        except (asyncio.TimeoutError, asyncio.QueueEmpty):
            return None

        
    ## child nodes ##
    # nats.subscriber(subject).json()
    def json(self):
        return SubscriberJsonNode(self)
        

    
class PublisherJsonNode(ControlNode):
    def __init__(self, publisher_node, headers = None):
        self.publisher_node = publisher_node
        self.headers_dict = dict(headers or {})
        

    async def aio_set(self, value):
        try:
            doc = json.dumps(value)
        except Exception as e:
            logger.warning(f'AsyncMQTT: publisher(): unable to convert to JSON: {e}')
            return None
        
        return await self.publisher_node.aio_set((self.headers_dict, doc))


    ## (virtual) child nodes ##
    def headers(self, headers):
        self.headers_dict = dict(headers)
        return self


    
class SubscriberJsonNode(ControlNode):
    def __init__(self, subscriber_node):
        self.subscriber_node = subscriber_node
        

    async def aio_get(self):
        message = await self.subscriber_node.aio_get()
        if message is None:
            return None, None

        headers = {
            'topic': message.topic.value,
            'message_id': message.mid,
        }
        if message.properties is not None and hasattr(message.properties, 'UserProperty'):
            for k,v in (message.properties.UserProperty or []):
                headers[k] = v
        
        body = message.payload
        if type(body) is bytes:
            try:
                body = body.decode()
            except:
                body = str(body)
            try:
                doc = json.loads(body)
            except:
                doc = body
                
        return (headers, doc)
