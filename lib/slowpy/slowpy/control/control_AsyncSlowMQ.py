# Created by Sanshiro Enomoto on 19 March 2026 #

import asyncio, json, uuid, time
from slowpy.control import ControlNode, ControlException

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SlowMQNode(ControlNode):
    def __init__(self, host:str, port:int=4222, *, name=None):
        self.host = host
        self.port = port
        self.name = name

        self.connections = set()
        self.publish_ws = None
        self.publish_retry_time = 0
        self.retry_wait = 10

        
    def __del__(self):
        for ws in self.connections:
            del ws


    async def aio_open(self):
        url = f'ws://{self.host}:{self.port}/ws/pubsub'
        if self.name is not None:
            url += f'?name={self.name}'
        try:
            import websockets
            ws = await websockets.connect(url)
        except Exception as e:
            logger.warning(f'AsyncSlowMQ Error: {url}: {e}')
            ws = None

        if ws is not None:
            self.connections.add(ws)

        return ws

    
    async def aio_close(self):
        for ws in self.connections:
            try:
                await ws.close()
            except (asyncio.CancelledError, Exception):
                pass
            del ws

        self.connections = set()

        
    def publish(self, topic):
        return PublishNode(self, topic)


    def subscribe(self, topic_filter, timeout=None):
        return SubscribeNode(self, topic_filter, timeout)

     
    async def _disconnect(self, ws):
        try:
            await ws.close()
            self.connections.discard(ws)
        except (asyncio.CancelledError, Exception):
            pass
        
        
    @classmethod
    def _node_creator_method(cls):
        def async_slowmq(self, host:str, port:int=18881, name:str=None):
            if True:
                return SlowMQNode(host, port, name=name)
            
            obj_name = '%s:%s' % (host, str(port))
            try:
                self._slowmq_nodes.keys()
            except:
                self._slowmq_nodes = {}
            node = self._slowmq_nodes.get(obj_name, None)
        
            if node is None:
                node = SlowMQNode(host, port)
                self._slowmq_nodes[obj_name] = node

            return node

        return async_slowmq

    
    
class PublishNode(ControlNode):
    def __init__(self, slowmq_node, topic):
        self.slowmq_node = slowmq_node
        self.topic = topic

        self.connected = False

        
    async def aio_set(self, value):
        if not self.connected:
            now = time.monotonic()
            if now - self.slowmq_node.publish_retry_time < self.slowmq_node.retry_wait:
                return
            self.slowmq_node.publish_retry_time = now
            
            if self.slowmq_node.publish_ws is not None:
                await self.slowmq_node._disconnect(self.slowmq_node.publish_ws)
            self.slowmq_node.publish_ws = await self.slowmq_node.aio_open()
            
            if self.slowmq_node.publish_ws is None:
                return
            else:
                self.connected = True
        
        doc = json.dumps({
            'headers': { 'topic': self.topic },
            'data': value
        })
        
        try:
            await self.slowmq_node.publish_ws.send(doc)
        except Exception as e:
            logger.warning(f'AsyncSlowMQ.publish(): {e}')
            self.connected = False
        except asyncio.CancelledError:
            pass
        

        
class SubscribeNode(ControlNode):
    def __init__(self, slowmq_node:SlowMQNode, topic_filter:str, timeout:float=None):
        self.slowmq_node = slowmq_node
        self.topic_filter = topic_filter
        self.timeout = timeout
        
        self.ws = None
        self.connected = False
        self.retry_time = 0


    async def _subscribe(self):
        ## use one websocket for each topic_filter ##
        
        if self.connected:
            return (self.ws is not None)

        now = time.monotonic()
        if now - self.retry_time < self.slowmq_node.retry_wait:
            return False
        self.retry_time = now
        
        if self.ws is not None:
            await self.slowmq_node._disconnect(self.ws)
        
        self.ws = await self.slowmq_node.aio_open()
        if self.ws is None:
            return False
        else:
            self.connected = True
        
        doc = json.dumps({
            'headers': {
                'action': 'subscribe',
                'topic': self.topic_filter,
                'message_id': str(uuid.uuid4()),
            },
            'data': None
        })
        
        try:
            await self.ws.send(doc)
            reply = await asyncio.wait_for(self.ws.recv(), timeout=1)
        except asyncio.TimeoutError:
            return False
        except Exception as e:
            logger.warning(f'AsyncSlowMQ.subscribe(): {e}')
            self.connected = False
            return False
        except asyncio.CancelledError:
            return False

        try:
            message = json.loads(reply)
        except Exception as e:
            logger.warning(f'AsyncSlowMQ.subscribe(): Invalid reply JSON: {e}: {reply}')
            return None
        
        if message.get('action') == 'error':
            msg = message.get('data',{}).get('message', '')
            logger.warning(f'AsyncSlowMQ.subscribe(): error reply: {msg}')
            self.connected = False
            return False
            
        return True
        
        
    async def aio_get(self):
        if not await self._subscribe():
            return None

        try:
            message = await asyncio.wait_for(self.ws.recv(), timeout=self.timeout)
        except asyncio.TimeoutError:
            message = None
        except asyncio.CancelledError:
            message = None
        except Exception as e:
            logger.warning(f'AsyncSlowMQ.subscribe().aio_get(): {e}')
            self.connected = False
            message = None
            await asyncio.sleep(1)
        if message is None:
            return None
        
        try:
            doc = json.loads(message)
        except Exception as e:
            logger.warning(f'AsyncSlowMQ.subscribe().aio_get(): Invalid reply JSON: {e}: {message}')
            return None

        return doc

    
    ## child nodes ##
    # slowmq.subscribe(subject).data()
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
            return msg.get('data', None)
