# Created by Sanshiro Enomoto on 17 March 2026 #

import asyncio, json, logging, traceback

import slowlette
from sd_component import Component


class SlowMQComponent(Component):
    def __init__(self, app, project):
        super().__init__(app, project)
        
        self.enabled = app.is_async
        
        self._next_client_id = 0
        self._websockets = {}     # client_id:int -> websocket
        self._clients = {}        # client_id:int -> { 'name': NAME }
        self._subscribers = {}    # topic_pattern:str -> set[client_id:int]
        self._send_failures = {}  # client_id:int -> consective failure count

        self._max_send_failures = 5
        

    def public_config(self):
        return { 'slowmq': {
            'enabled': self.enabled,
            'attached': { topic:len(clients) for topic,clients in self._subscribers.items() },
        }}

    
    @slowlette.websocket('/ws/slowmq')
    async def connect(self, websocket:slowlette.WebSocket, name:str=None):
        try:
            await websocket.accept()
        except Exception as e:
            logging.warning(f'Unable to accept slowmq websocket: {e}')
            return None

        client_id = await self.add_client(name, websocket)
        name = self._clients[client_id].get('name')
        
        try:
            while True:
                message = await websocket.receive()
                if message is not None and len(message) > 0:
                    try:
                        doc = json.loads(message)
                        headers = doc['headers']
                    except Exception as e:
                        logging.warning(f'Bad SlowMQ Message: {name}: {repr(message)}: {e}')
                        continue
                    else:
                        logging.debug(f'SlowMQ Message Received: {name}: {repr(message)}')
                    await self.handle_message(client_id, headers, message)
        except slowlette.ConnectionClosed:
            logging.info(f'SlowMQ WebSocket Closed: {name}')
        except Exception as e:
            logging.warning(f'SlowMQ WebSocket Closed by error: {e}')
            logging.info(traceback.format_exc())
        finally:
            await self.remove_client(client_id)

        
    async def add_client(self, name:str, websocket)->int:
        client_id = self._next_client_id
        self._next_client_id += 1
        
        if name is None:
            name = f'AnonymousClient{client_id:02d}'
            
        self._clients[client_id] = { 'name': name }
        self._websockets[client_id] = websocket
        self._send_failures[client_id] = 0
        
        logging.info(f'SlowMQ WebSocket Connected: {name} (id:{client_id})')

        return client_id
        
        
    async def remove_client(self, client_id:int):
        self._websockets.pop(client_id, None)
        self._send_failures.pop(client_id, None)
        
        for topic in list(self._subscribers):
            await self.unsubscribe(client_id, topic)
        self._clients.pop(client_id, None)
            
        
    async def reply_error(self, client_id:int, headers, message):
        websocket = self._websockets.get(client_id)
        if websocket is None:
            return
        reply_to = headers.get('message_id', None)
        if reply_to is None:
            return

        await websocket.send(json.dumps({
            'headers': {
                'action': 'error',
                'reply_to': reply_to,
            },
            'data':{
                'message': message
            }
        }))
            
        
    async def handle_message(self, client_id:int, headers, message):
        topic = headers.get('topic')
        if topic is None or len(topic) == 0:
            return False

        action = headers.get('action', 'publish')
        if action == 'publish':
            return await self.publish(topic, message, headers)
        
        if action == 'subscribe':
            return await self.subscribe(client_id, topic, headers)
        
        if action == 'unsubscribe':
            return await self.unsubscribe(client_id, topic, headers)


    async def subscribe(self, client_id:int, topic:str, headers):
        try:
            self.validate_topic_pattern(topic)
        except Exception as e:
            logging.warning(f'SlowMQ: {e}')
            await self.reply_error(client_id, headers, str(e))
            return False
        
        if topic not in self._subscribers:
            self._subscribers[topic] = set()
            
        self._subscribers[topic].add(client_id)
        logging.info(f'SlowMQ Subscription: {topic} <- {self._clients[client_id]["name"]}')

        websocket = self._websockets.get(client_id)
        reply_to = headers.get('message_id')
        if websocket is not None and reply_to is not None:
            await websocket.send(json.dumps({
                'headers': {
                    'action': 'reply',
                    'reply_to': reply_to,
                },
                'data': None
            }))
                                 
        return True
        
    
    async def unsubscribe(self, client_id:int, topic:str, headers=None):
        if topic not in self._subscribers:
            await self.reply_error(client_id, headers or {}, f'unknown topic "{topic}"')
            return False

        if client_id not in self._subscribers[topic]:
            await self.reply_error(client_id, headers or {}, f'not registered to the topic "{topic}"')
            return False

        self._subscribers[topic].discard(client_id)
        logging.info(f'SlowMQ Cancel Subscription: {topic} <- {self._clients[client_id]["name"]}')

        if len(self._subscribers[topic]) == 0:
            del self._subscribers[topic]
    
        return True

    
    async def publish(self, topic:str, message, headers):
        receivers = []
        for topic_pattern, subscribers in self._subscribers.items():
            if self.topic_match(topic_pattern, topic):
                for client_id in subscribers:
                    websocket = self._websockets.get(client_id)
                    if websocket is not None:
                        receivers.append((client_id, websocket))

        results = await asyncio.gather(*(ws.send(message) for _, ws in receivers), return_exceptions=True)
        
        stale_clients = []
        for (client_id, _), result in zip(receivers, results):
            if not isinstance(result, Exception):
                self._send_failures[client_id] = 0
            else:
                count = self._send_failures.get(client_id, 0) + 1
                self._send_failures[client_id] = count
                client_name = self._clients.get(cilent_id, {}).get('name')
                logging.warning(f'SlowMQ Publish (topic:{topic}, client:{client_name}, n:{count}): {result}')
                if count > self._max_send_failures:
                    stale_clients.append(client_id)

        for client_id in stale_clients:            
            websocket = self._websockets.get(client_id)
            if websocket is not None:
                try:
                    await websocket.close()
                except Exception:
                    pass                
            client_name = self._clients.get(cilent_id, {}).get('name')
            await self.remove_client(client_id)
            logging.warning(f'SlowMQ: Client removed due to too many send failures: {client_name}')
                    
        
    def validate_topic_pattern(self, pattern:str):
        """
        NATS-like topic wildcard pattern
        Rules:
          - tokens are separated by '.'
          - '*' matches exactly one token
          - '>' matches zero or more trailing tokens
          - '>' must appear only as the last token
          - no partial-token wildcard is allowed
        Examples:
          - topic_match("foo.*.baz", "foo.bar.baz") == True
          - topic_match("foo.>", "foo") == True
          - topic_match("foo.>", "foo.bar.baz") == True
          - topic_match("foo.*", "foo") == False
        """
        
        tokens = pattern.split(".") if pattern else []
        for i, token in enumerate(tokens):
            if token == ">":
                if i != len(tokens) - 1:
                    raise ValueError("Invalid topic pattern: '>' must be the last token")
            elif ("*" in token) or (">" in token):
                if token != "*":
                    raise ValueError("Invalid topic  pattern: wildcards must occupy an entire token")

        
    def topic_match(self, pattern:str, topic:str)->bool:
        pattern_tokens = pattern.split(".") if pattern else []
        topic_tokens = topic.split(".") if topic else []

        k_pattern = 0  # index for pattern
        k_topic = 0  # index for topic

        while k_pattern < len(pattern_tokens):
            ptoken = pattern_tokens[k_pattern]

            if ptoken == ">":
                # Matches the rest, including zero tokens
                return True

            if k_topic >= len(topic_tokens):
                # Topic ended before pattern did
                return False

            if ptoken == "*":
                k_pattern += 1
                k_topic += 1
                continue

            if ptoken != topic_tokens[k_topic]:
                return False

            k_pattern += 1
            k_topic += 1

        # Pattern consumed; topic must also be fully consumed
        return k_topic == len(topic_tokens)
