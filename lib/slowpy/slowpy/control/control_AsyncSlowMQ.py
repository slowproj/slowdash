# Created by Sanshiro Enomoto on 19 March 2026 #

import asyncio, json, uuid, time
from slowpy.control import ControlNode, ControlException

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SlowMQNode(ControlNode):
    def __init__(self, url:str, *, name=None):
        self.url = url
        self.name = name

        self.connections = set()
        self.publisher_ws = None
        self.publisher_retry_time = 0
        self.retry_wait = 10

        self.publisher_ws_connected = False

        
    def __del__(self):
        for ws in self.connections:
            del ws


    async def aio_open(self):
        if self.url.startswith('slowmq://'):
            netloc = self.url[len('slowmq://'):]
            ws_prot = 'ws'
        elif self.url.startswith('slowmqs://'):
            netloc = self.url[len('slowmqs://'):]
            ws_prot = 'wss'
        else:
            logger.warning(f'AsyncSlowMQ Error: {self.url}: bad SlowMQ URL: must start with slowmq:// or slowmqs://')
            return None
            
        if netloc.endswith('/'):
            netloc = netloc[:-1]
        wsurl = f'{ws_prot}://{netloc}/ws/pubsub'
        if self.name is not None:
            wsurl += f'?name={self.name}'
            
        try:
            import websockets
            ws = await websockets.connect(wsurl)
        except Exception as e:
            logger.warning(f'AsyncSlowMQ Error: {self.url}: {e}')
            ws = None
        else:
            logger.info(f'AsyncSlowMQ: connected: {self.url}')

        if ws is not None:
            self.connections.add(ws)

        return ws

    
    async def aio_close(self):
        is_cancelled = False
        for ws in self.connections:
            try:
                await ws.close()
            except asyncio.CancelledError as e:
                is_cancelled = True
            except Exception:
                pass
            del ws

        self.connections = set()

        if is_cancelled:
            raise asyncio.CancelledError

        
    def publisher(self, topic):
        return PublisherNode(self, topic)


    def subscriber(self, topic_filter, timeout=None):
        return SubscriberNode(self, topic_filter, timeout)

     
    async def _disconnect(self, ws):
        is_cancelled = False
        
        try:
            await ws.close()
            self.connections.discard(ws)
        except asyncio.CancelledError as e:
            is_cancelled = True
        except Exception:
            pass
        
        if is_cancelled:
            raise asyncio.CancelledError

        
    @classmethod
    def _node_creator_method(cls):
        def async_slowmq(self, url:str, name:str=None):
            if True:
                return SlowMQNode(url, name=name)
            
            obj_name = url
            try:
                self._slowmq_nodes.keys()
            except:
                self._slowmq_nodes = {}
            node = self._slowmq_nodes.get(obj_name, None)
        
            if node is None:
                node = SlowMQNode(url)
                self._slowmq_nodes[obj_name] = node

            return node

        return async_slowmq

    
    
class PublisherNode(ControlNode):
    def __init__(self, slowmq_node, topic):
        self.slowmq_node = slowmq_node
        self.topic = topic

        
    async def aio_set(self, value):
        if not self.slowmq_node.publisher_ws_connected:
            now = time.monotonic()
            if now - self.slowmq_node.publisher_retry_time < self.slowmq_node.retry_wait:
                return
            self.slowmq_node.publisher_retry_time = now
            
            if self.slowmq_node.publisher_ws is not None:
                await self.slowmq_node._disconnect(self.slowmq_node.publisher_ws)
            self.slowmq_node.publisher_ws = await self.slowmq_node.aio_open()
            
            if self.slowmq_node.publisher_ws is None:
                return
            else:
                self.slowmq_node.publisher_ws_connected = True

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
        headers['topic'] = self.topic
            
        try:
            doc = json.dumps({
                'headers': headers,
                'data': body
            })
        except Exception as e:
            logger.warning(f'AsyncSlowMQ.publisher(): unable to convert to JSON: {e}')
            return
        
        try:
            await self.slowmq_node.publisher_ws.send(doc)
        except Exception as e:
            logger.warning(f'AsyncSlowMQ.publisher(): {e}')
            self.slowmq_node.publisher_ws_connected = False

        
    ## child nodes ##
    # nats.publisher(subject).json()
    def json(self, headers=None):
        return PublisherJsonNode(self, headers)
        

        
class SubscriberNode(ControlNode):
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
            logger.warning(f'AsyncSlowMQ.subscriber(): {e}')
            self.connected = False
            return False

        try:
            message = json.loads(reply)
        except Exception as e:
            logger.warning(f'AsyncSlowMQ.subscriber(): Invalid reply JSON: {e}: {reply}')
            return None
        
        if message.get('headers', {}).get('action') == 'error':
            msg = message.get('data', {}).get('message', '')
            logger.warning(f'AsyncSlowMQ.subscriber(): error reply: {msg}')
            self.connected = False
            return False
            
        return True
        
        
    async def aio_get(self):
        if not await self._subscribe():
            await asyncio.sleep(1)
            return None

        try:
            message = await asyncio.wait_for(self.ws.recv(), timeout=self.timeout)
        except asyncio.TimeoutError:
            message = None
        except Exception as e:
            logger.warning(f'AsyncSlowMQ.subscriber().aio_get(): {e}')
            self.connected = False
            message = None
            await asyncio.sleep(1)
        if message is None:
            return None
        
        try:
            doc = json.loads(message)
        except Exception as e:
            logger.warning(f'AsyncSlowMQ.subscriber().aio_get(): Invalid reply JSON: {e}: {message}')
            return None

        return doc

        
    ## child nodes ##
    # nats.subscriber(subject).json()
    def json(self):
        return SubscriberJsonNode(self)
        

    
class PublisherJsonNode(ControlNode):
    def __init__(self, publisher_node, headers=None):
        self.publisher_node = publisher_node
        self.headers_dict = dict(headers or {})
        

    async def aio_set(self, value):
        return await self.publisher_node.aio_set((self.headers_dict, value))


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
        
        headers = message.get('headers', {})
        body = message.get('data')
                
        return (headers, body)
