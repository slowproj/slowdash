# Created by Sanshiro Enomoto on 27 September 2025 #


from slowpy.control import ControlNode
import asyncio, time, uuid, json, typing, inspect, logging


class Message(typing.NamedTuple):
    body: dict[str,typing.Any] | str | bytes | None = None
    header: dict[str, typing.Any] = {}
    parameters: dict[str, typing.Any] = {}
    


class RabbitMQNode(ControlNode):
    def __init__(self, url:str):
        import aio_pika as aio_pika
        self.aio_pika = aio_pika
        
        self.url = url
        self.connection = None
        self.channel = None

        
    async def _construct(self):
        if self.connection is None:
            try:
                self.connection = await self.aio_pika.connect_robust(self.url)
                self.channel = await self.connection.channel()
            except Exception as e:
                logging.error(f'unable to connect to RabbitMQ: {self.url}: {e}')
                self.connection = False
                self.channel = False
        
            
    ## child nodes ##
    # rabbitmq().direct_exchange(name, **kwargs)  kwargs{durable:bool=False}
    def direct_exchange(self, name:str, **kwargs):
        return ExchangeNode(self, self.aio_pika.ExchangeType.DIRECT, name, **kwargs)


    # rabbitmq().topic_exchange(name, **kwargs)
    def topic_exchange(self, name:str, **kwargs):
        return ExchangeNode(self, self.aio_pika.ExchangeType.TOPIC, name, **kwargs)


    # rabbitmq().fanout_exchange(name, **kwargs)
    def fanout_exchange(self, name:str, **kwargs):
        return ExchangeNode(self, self.aio_pika.ExchangeType.FANOUT, name, **kwargs)


    @classmethod
    def _node_creator_method(cls):
        def rabbitmq(self, url:str):
            try:
                self._rmq_nodes.keys()
            except:
                self._rmq_nodes = {}
            node = self._rmq_nodes.get(url, None)
        
            if node is None:
                node = RabbitMQNode(url)
                self._rmq_nodes[url] = node

            return node

        return rabbitmq

    

class ExchangeNode(ControlNode):
    def __init__(self, rmq_node:RabbitMQNode, exchange_type, name:str, **kwargs):
        self.rmq_node = rmq_node
        self.exchange_type = exchange_type
        self.name = name
        self.kwargs = {k:v for k,v in kwargs.items()}
        
        self.exchange = None

        
    async def _construct(self):
        if self.exchange is None:
            await self.rmq_node._construct()
            if self.rmq_node.channel is False:
                self.exchange = False
            else:
                self.exchange = await self.rmq_node.channel.declare_exchange(self.name, self.exchange_type, **self.kwargs)
        
        
    ## child nodes ##
    # rabbitmq().XXX_exchange(name).publish(routing_key:str)
    def publish(self, routing_key:str, *, parameters={}, **kwargs):
        return PublishNode(self, routing_key, parameters=parameters, **kwargs)

    # rabbitmq().XXX_exchange(name).queue(name, routing_key, **kwargs)  kwargs{exclusive:bool=False}
    def queue(self, name:str, *, routing_key:str=None, handler=None, timeout=0, **kwargs):
        return QueueNode(self, name, routing_key=routing_key, handler=handler, timeout=timeout, **kwargs)


    
class PublishNode(ControlNode):
    def __init__(self, exchange_node:ExchangeNode, routing_key, *, parameters={}, **kwargs):
        self.exchange_node = exchange_node
        self.routing_key = routing_key
        self.parameters = parameters
        self.kwargs = {k:v for k,v in kwargs.items()}


    async def aio_set(self, value):
        if self.exchange_node.exchange is None:
            await self.exchange_node._construct()
        if self.exchange_node.exchange is False:
            return None
            
        body, headers, parameters = ({}, {}, {})
        if type(value) is Message:
            body, headers, parameters = value
        elif type(value) is tuple:
            if len(value) == 1:
                body, = value
            elif len(value) == 2:
                body, headers = value
            elif len(value) == 3:
                body, headers, parameters = value
        else:
            body = value

        if type(body) is str:
            content_type = 'text/plain'
            body = body.encode()
        elif type(body) in [ list, dict ]:
            content_type = 'application/json'
            body = json.dumps(body).encode()
        else:
            content_type = 'application/octet-stream'

        for k,v in self.parameters.items():
            if k not in parameters:
                parameters[k] = v
        if 'message_id' not in parameters:
            parameters['message_id'] = f'{uuid.uuid4()}'
        if 'content_type' not in parameters:
            parameters['content_type'] = content_type

        await self.exchange_node.exchange.publish(
            self.exchange_node.rmq_node.aio_pika.Message(
                body,
                headers = headers,
                **parameters
            ),
            self.routing_key,
            **self.kwargs
        )
        
        

class QueueNode(ControlNode):
    def __init__(self, exchange_node:ExchangeNode, queue_name:str, *, routing_key:str=None, handler=None, timeout=0, **kwargs):
        self.exchange_node = exchange_node
        self.name = queue_name
        self.routing_key = routing_key or queue_name
        self.timeout = timeout
        self.kwargs = {k:v for k,v in kwargs.items()}
        
        async def _default_handler(message):
            parameters = {
                'message_id': message.message_id,
                'timestamp': message.timestamp,
                'content_type': message.content_type,
                'content_encoding': message.content_encoding,
                'correlation_id': message.correlation_id,
                'reply_to': message.reply_to,
            }
            if message.content_type == 'application/json':
                return Message(json.loads(message.body.decode()), message.headers, parameters)
            elif message.content_type == 'text/plain':
                return Message(message.body.decode(), message.headers, parameters)
            else:
                return Message(message.body, message.headers, parameters)

        self.handler = handler or _default_handler
        self.queue = None


    async def _construct(self):
        if self.queue is None:
            await self.exchange_node._construct()
            if self.exchange_node.rmq_node.channel is False:
                self.queue = False
            else:
                self.queue = await self.exchange_node.rmq_node.channel.declare_queue(self.name, **self.kwargs)
                await self.queue.bind(self.exchange_node.exchange, routing_key = self.routing_key)

        
    async def aio_get(self):
        if self.queue is None:
            await self._construct()
        if self.queue is False:
            return Message()

        message = None
        tries = 0
        while True:
            try:
                message = await self.queue.get(fail=False)
                if message is not None:
                    break
                if self.is_stop_requested():
                    break
                if self.timeout > 0 and tries > self.timeout:
                    logging.warn('AMQP Queue Timeout')
                    break
                tries += 1
                await asyncio.sleep(1)
            except: # asyncio.exceptions.CancelledError
                break

        if message is None:
            return Message()

        async with message.process(requeue=False):  # ACK will be sent automatically by process()
            return await self.handler(message)


    # rabbitmq().direct_exchange(name).rpc_function(name, function)
    def rpc_function(self, function):
        return RpcFunctionNode(self, function)

    # rabbitmq().direct_exchange(name).queue(name).rpc_call(routing_key)
    def rpc_call(self, routing_key:str, body={}, headers={}, parameters={}):
        return RpcCallNode(self, routing_key, body, headers, parameters)


    
class RpcFunctionNode(ControlNode):
    def __init__(self, queue_node:QueueNode, function):
        self.queue_node = queue_node
        self.function = function

        
    async def aio_get(self):
        request_message = await self.queue_node.aio_get()
        if request_message.body is None:
            return None
        
        if inspect.iscoroutinefunction(self.function):
            return_value = await self.function(request_message)
        else:
            return_value = self.function(request_message)

        routing_key = request_message.parameters.get('reply_to', None)
        if routing_key is not None:
            parameters = {
                'correlation_id': request_message.parameters.get('correlation_id', None),
            }
            publish_node = self.queue_node.exchange_node.publish(routing_key, parameters=parameters)
            await publish_node.aio_set(return_value)

        return return_value



class RpcCallNode(ControlNode):
    def __init__(self, queue_node:QueueNode, routing_key:str, body={}, headers={}, parameters={}):
        self.queue_node = queue_node
        self.routing_key = routing_key
        self.body = body
        self.headers = headers
        self.parameters = parameters

        
    async def aio_get(self):
        publish_node = self.queue_node.exchange_node.publish(routing_key=self.routing_key)
        parameters = { k:v for k,v in self.parameters.items() }
        parameters['reply_to'] = self.queue_node.routing_key
        parameters['correlation_id'] = f'{uuid.uuid4()}'        
        await publish_node.aio_set((self.body, self.headers, parameters))

        # BUG: there might be multiple reply messages (e.g., by topic/fanout exchange)
        return await self.queue_node.aio_get()        
