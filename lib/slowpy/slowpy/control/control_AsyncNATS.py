# Created by Sanshiro Enomoto on 16 March 2026 #

import asyncio
from slowpy.control import ControlNode, ControlException

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class NATSNode(ControlNode):
    def __init__(self, host:str, port:int=4222):
        self.host = host
        self.port = port
        
        self.connected = False
        self.client = None
        self.connect_lock = asyncio.Lock()
        
        
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

            if self.client is None:
                url = f'nats://{self.host}:{self.port}'
                try:
                    import nats
                    self.client = await nats.connect(url)
                except Exception as e:
                    logging.error(f'NATS: {url}: {e}')
                    self.client = None
                    return False
            
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
                return None
    
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
