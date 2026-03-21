# Created by Sanshiro Enomoto on 16 March 2026 #

import asyncio, time
from slowpy.control import ControlNode, ControlException

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class NATSNode(ControlNode):
    def __init__(self, host:str, port:int=4222):
        self.host = host
        self.port = port
        
        self.client = None
        self.connected = False
        self.connect_lock = asyncio.Lock()
        self.retry_wait = 10
        self.last_connect_attempt_time = 0
        
        
    def __del__(self):
        if self.client:
            del self.client


    async def aio_close(self):
        if self.client is None:
            return

        try:
            await self.client.drain()
        except:
            pass
        
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

            if self.client is None:
                url = f'nats://{self.host}:{self.port}' 
                async def error_cb(e):
                    logging.warning(f'NATS: ERROR: {url}: {e}')
                async def disconnected_cb():
                    logging.warning(f'NATS: disconnected: {url}')
                async def reconnected_cb():
                    logging.warning(f'NATS: reconnected: {url}')
                async def closed_cb():
                    logging.warning(f'NATS: permanently closed (no reconnection): {url}')
                try:
                    import nats
                    self.client = await nats.connect(
                        url,
                        allow_reconnect=True, reconnect_time_wait=self.retry_wait, max_reconnect_attempts=-1,
                        ping_interval=30, max_outstanding_pings=3,
                        error_cb = error_cb, closed_cb = closed_cb,
                        disconnected_cb = disconnected_cb, reconnected_cb = reconnected_cb
                    )
                except Exception as e:
                    logging.error(f'NATS: {url}: {e}')
                    self.client = None
                    return False
                else:
                    logging.info(f'NATS: connected: {url}')
            
            self.connected = True
            
            return True
    
        
    @classmethod
    def _node_creator_method(cls):
        def async_nats(self, host:str, port:int=4222):
            if True:
                return NATSNode(host, port)
            
            name = '%s:%s' % (host, str(port))
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

    
    
class PublishNode(ControlNode):
    def __init__(self, nats_node, topic):
        self.nats_node = nats_node
        self.topic = topic

        
    async def aio_set(self, value):
        if not await self.nats_node.aio_do_connect():
            return None

        try:
            await self.nats_node.client.publish(self.topic, value)
        except Exception as e:
            logging.error(f'NATS.publish(): {e}')
        except asyncio.CancelledError:
            pass
        

        
class SubscribeNode(ControlNode):
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


    async def aio_do_register(self):
        async with self.register_lock:
            if self.registered:
                return True
            if not await self.nats_node.aio_do_connect():
                return False
    
            async def message_handler(msg):
                topic, message = msg.subject, msg.data
                logger.debug(f'NATS message: ({topic}) {message.decode()}')
                result = self.handler(msg)
                if asyncio.iscoroutine(result):
                    await result

            try:
                await self.nats_node.client.subscribe(self.topic_filter, cb=message_handler)
            except Exception as e:
                logging.warning(f'NATS.subscribe(): {e}')
                return False
            else:
                self.registered = True
                
            return True

        
    async def aio_has_data(self):
        if not await self.aio_do_register():
            return False
            
        return not await self.queue.empty()

        
    async def aio_get(self):
        if not await self.aio_do_register():
            asyncio.sleep(1)
            return None

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
    # nats.subscribe(subject).data()
    def data(self):
        return SubscribeDataNode(self)
        

    
class SubscribeDataNode(ControlNode):
    def __init__(self, subscribe_node):
        self.subscribe_node = subscribe_node
        

    async def aio_get(self):
        msg = await self.subscribe_node.aio_get()
        if msg is None:
            return None
        else:
            return msg.data
