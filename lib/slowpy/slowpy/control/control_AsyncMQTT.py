# Created by Sanshiro Enomoto on 13 March 2026 #

import asyncio
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
        
        import aiomqtt
        self.client = aiomqtt.Client(self.host, self.port, keepalive=self.keepalive)
        
        self.connected = False
        self.receiver_task = None

        
    def __del__(self):
        if self.receiver_task is not None:
            self.receiver_task.cancel()
        if self.client:
            del self.client


    async def aio_close(self):
        if self.client is None:
            return

        try:
            if self.receiver_task is not None:
                self.receiver_task.cancel()
                self.receiver_task = None
        except:
            pass

        try:
            if self.connected:
                await self.client.__aexit__(None, None, None)
                logger.info(f'MQTT Connection Closed')
        except:
            pass
            
        del self.client
        self.client = None

        
    def publish(self, topic):
        return PublishNode(self, topic)


    def subscribe(self, topic_filter, handler=None, timeout=None):
        return SubscribeNode(self, topic_filter, handler, timeout)

     
    async def aio_do_connect(self):
        if self.client is None:
            return False
        if self.connected:
            return True
        
        try:
            await self.client.__aenter__()
        except Exception as e:
            logger.error(f'Unable to connect to MQTT broker: {e}')
            return False
        else:
            logger.info(f'MQTT broker connected')
            
        self.connected = True
        
        if self.receiver_task is not None:
            self.receiver_task.cancel()

        async def receiver():
            async for msg in self.client.messages:
                logger.debug(f'MQTT message: ({msg.topic}) {msg.payload.decode()}')
                topic, message = str(msg.topic), msg.payload.decode()
                for topic_filter, subscribers in self.subscribers.items():
                    if not msg.topic.matches(topic_filter):
                        continue
                    logger.debug(f'MQTT message topic matches: {msg.topic} ~ {topic_filter}')
                    for subscriber in subscribers:
                        await subscriber.aio_do_handle(topic, message)

        self.receiver_task = asyncio.create_task(receiver())

        return True
    
        
    async def aio_do_subscribe(self, topic_filter, subscribe_node):
        if not await self.aio_do_connect():
            return
        
        if topic_filter not in self.subscribers:
            logger.debug(f'MQTT subscribe: {topic_filter}')
            await self.client.subscribe(topic_filter)
            self.subscribers[topic_filter] = []
            
        self.subscribers[topic_filter].append(subscribe_node)
        
     
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
    
        await self.mqtt.client.publish(self.topic, value)
        

        
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
        
        async def default_handler(topic:str, message:str):
            await self.queue.put(message)
        self.handler = handler or default_handler
        
        self.registered = False

        
    async def aio_do_handle(self, topic:str, message:str):
        result = self.handler(topic, message)
        if asyncio.iscoroutine(result):
            await result


    async def aio_has_data(self):
        if not self.registered:
            await self.mqtt.aio_do_subscribe(self.topic_filter, self)
            self.registered = True
            
        return not await self.queue.empty()

        
    async def aio_get(self):
        if not self.registered:
            await self.mqtt.aio_do_subscribe(self.topic_filter, self)
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
            
        
            
if __name__ == '__main__':
    """
    Chat example
    """
    
    import sys
    from slowpy.control import control_system as ctrl

    async def main():
        mqtt = ctrl.import_control_module('AsyncMQTT').async_mqtt('localhost')
        is_running = True

        async def reader():
            nonlocal is_running
            sub = mqtt.subscribe('chat/#', timeout=0.1)
            while is_running:
                message = await sub.aio_get()
                if message is not None:
                    sys.stdout.write(f'\n{message}\n> ')

        async def writer():
            nonlocal is_running
            async def ainput(prompot=""):
                try:
                    return await asyncio.to_thread(input, prompot)
                except:
                    return None
    
            while is_running:
                line = await ainput('> ')
                if line is None:
                    is_running = False
                else:
                    await mqtt.publish('chat/all').aio_set(line)

        await asyncio.gather(reader(), writer())
        await mqtt.aio_close()
        
    asyncio.run(main())
