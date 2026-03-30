# Created by Sanshiro Enomoto on 16 March 2026 #

import asyncio, time, json
from slowpy.control import ControlNode, ControlException

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class NATSNode(ControlNode):
    def __init__(self, url:str):
        self.url = url
        
        self.client = None
        self.connected = False
        self.connect_lock = asyncio.Lock()
        self.retry_wait = 10
        self.last_connect_attempt_time = 0
        
        
    def __del__(self):
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

            if self.client is None:
                async def error_cb(e):
                    logger.warning(f'AsyncNATS: ERROR: {self.url}: {e}')
                async def disconnected_cb():
                    logger.info(f'AsyncNATS: disconnected: {self.url}')
                async def reconnected_cb():
                    logger.info(f'AsyncNATS: reconnected: {self.url}')
                async def closed_cb():
                    logger.info(f'AsyncNATS: permanently closed (no reconnection): {self.url}')
                try:
                    import nats
                    self.client = await nats.connect(
                        self.url,
                        allow_reconnect=True, reconnect_time_wait=self.retry_wait, max_reconnect_attempts=-1,
                        ping_interval=30, max_outstanding_pings=3,
                        error_cb = error_cb, closed_cb = closed_cb,
                        disconnected_cb = disconnected_cb, reconnected_cb = reconnected_cb
                    )
                except Exception as e:
                    logger.error(f'AsyncNATS: {self.url}: {e}')
                    self.client = None
                    return False
                else:
                    logger.info(f'AsyncNATS: connected: {self.url}')
            
            self.connected = True
            
            return True
    
        
    async def aio_close(self):
        if self.client is None:
            return

        try:
            await self.client.drain()
        except:
            pass
        
        del self.client
        self.client = None

        
    def publisher(self, topic):
        return PublisherNode(self, topic)


    def subscriber(self, topic_filter, handler=None, timeout=None):
        return SubscriberNode(self, topic_filter, handler, timeout)

     
    @classmethod
    def _node_creator_method(cls):
        def async_nats(self, url:str):
            if True:
                return NATSNode(url)
            
            name = url
            try:
                self._nats_nodes.keys()
            except:
                self._nats_nodes = {}
            node = self._nats_nodes.get(name, None)
        
            if node is None:
                node = NATSNode(host, port)
                self._nats_nodes[name] = node

            return node

        return async_nats

    
    
class PublisherNode(ControlNode):
    def __init__(self, nats_node, topic):
        self.nats_node = nats_node
        self.topic = topic

        
    async def aio_set(self, value):
        if not await self.nats_node.aio_open():
            return None

        body, headers = (None, {})
        if type(value) is tuple:
            if len(value) == 1:
                (body,) = value
            elif len(value) == 2:
                headers, body = value
        else:
            body = value
        if headers is None:
            headers = {}

        try:
            await self.nats_node.client.publish(self.topic, body, headers=headers)
        except Exception as e:
            logger.error(f'AsnncNATS.publisher(): {e}')

        
    ## child nodes ##
    # nats.publisher(subject).json()
    def json(self, headers=None):
        return PublisherJsonNode(self, headers)


    
class SubscriberNode(ControlNode):
    def __init__(self, nats_node:NATSNode, topic_filter:str, handler=None, timeout=None):
        """
        - If handler is not None, it is called on receiving a message.
        - Otherwise, the received messages are queued, which can be retrieved by has_data()/get()
        """

        self.nats_node = nats_node
        self.topic_filter = topic_filter
        self.timeout = timeout
        
        self.queue = asyncio.Queue(maxsize=1024)
        
        async def default_handler(message):
            await self.queue.put(message)
        self.handler = handler or default_handler
        
        self.registered = False
        self.register_lock = asyncio.Lock()


    async def _register(self):
        async with self.register_lock:
            if self.registered:
                return True
            if not await self.nats_node.aio_open():
                return False
    
            async def message_handler(msg):
                topic, message = msg.subject, msg.data
                logger.debug(f'AsyncNATS message: ({topic}) {message.decode()}')
                try:
                    result = self.handler(msg)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    logging.error('AsyncNATS: error in message handler: {e}')
                        

            try:
                await self.nats_node.client.subscribe(self.topic_filter, cb=message_handler)
            except Exception as e:
                logger.warning(f'AsyncNATS.subscribe(): {e}')
                return False
            else:
                self.registered = True
                
            return True

        
    async def aio_has_data(self):
        if not await self._register():
            return False
            
        return not await self.queue.empty()

        
    async def aio_get(self):
        if not await self._register():
            await asyncio.sleep(1)
            return None

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
    def __init__(self, publisher_node, headers=None):
        self.publisher_node = publisher_node
        self.headers_dict = dict(headers or {})
        

    async def aio_set(self, value):
        try:
            doc = json.dumps(value)
        except Exception as e:
            logger.warning(f'AsyncNATS: publisher(): unable to convert to JSON: {e}')
            return None
        
        return await self.publisher_node.aio_set((self.headers_dict, doc.encode()))


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
            'topic': message.subject,
        }
        headers.update(message.headers)
        
        body = message.data
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
