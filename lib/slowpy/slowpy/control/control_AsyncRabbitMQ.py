# Created by Sanshiro Enomoto on 27 September 2025 #

from slowpy.control import ControlNode, ControlException
import asyncio, time, uuid, json, typing, inspect, logging
import aio_pika


class Message(typing.NamedTuple):
    body: dict[str,typing.Any] | str | bytes | None = None
    headers: dict[str, typing.Any] = {}
    parameters: dict[str, typing.Any] = {}
    


class RabbitMQNode(ControlNode):
    def __init__(self, url:str, *, qos_prefetch_count=32):
        self.url = url
        self.prefetch_count = qos_prefetch_count
        
        self.connection = None
        self.channel = None
        self.is_retry = False

        
    async def _construct(self):
        if self.connection is None:
            if self.is_retry:
                logging.info(f'RabbitMQ: retrying to connect to {self.url}')
            try:
                self.connection = await aio_pika.connect_robust(self.url)
                self.channel = await self.connection.channel()
                self.is_retry = False
            except Exception as e:
                if not self.is_retry:
                    logging.error(f'unable to connect to RabbitMQ: {self.url}: {e}')
                    self.is_retry = True
                else:
                    logging.info(f'unable to connect to RabbitMQ: {self.url}: {e}')
                self.connection = None
                self.channel = None
                return
                
            try:
                await self.channel.set_qos(prefetch_count=self.prefetch_count)
            except Exception as e:
                logging.warning(f'RabbitMQ: unable to set QoS prefetch count ({self.prefetch_count}): {e}')
        
            
    ## child nodes ##
    # rabbitmq().direct_exchange(name, **kwargs)  kwargs{durable:bool=False}
    def direct_exchange(self, name:str, **kwargs):
        return ExchangeNode(self, aio_pika.ExchangeType.DIRECT, name, **kwargs)


    # rabbitmq().topic_exchange(name, **kwargs)
    def topic_exchange(self, name:str, **kwargs):
        return ExchangeNode(self, aio_pika.ExchangeType.TOPIC, name, **kwargs)


    # rabbitmq().fanout_exchange(name, **kwargs)
    def fanout_exchange(self, name:str, **kwargs):
        return ExchangeNode(self, aio_pika.ExchangeType.FANOUT, name, **kwargs)


    @classmethod
    def _node_creator_method(cls):
        def rabbitmq(self, url:str, **kwargs):
            try:
                self._rmq_nodes.keys()
            except:
                self._rmq_nodes = {}
            node = self._rmq_nodes.get(url, None)
        
            if node is None:
                node = RabbitMQNode(url, **kwargs)
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
            if self.rmq_node.channel is None:
                await self.rmq_node._construct()
            if self.rmq_node.channel is None:
                return   # error, retry later
            else:
                try:
                    self.exchange = await self.rmq_node.channel.declare_exchange(
                        self.name,
                        self.exchange_type,
                        **self.kwargs
                    )
                except Exception as e:
                    logging.error(f'RabbitMQ: failed to declare exchange {self.name}: {e}')
                    self.exchange = None
                    
        
    ## child nodes ##
    # rabbitmq().XXX_exchange(name).publish(routing_key:str)
    def publish(self, routing_key:str, *, parameters=None, **kwargs):
        return PublishNode(self, routing_key, parameters=parameters, **kwargs)

    # rabbitmq().XXX_exchange(name).queue(name, routing_key, **kwargs)  kwargs{exclusive:bool=False}
    def queue(self, name:str, *, routing_key:str=None, handler=None, timeout=0, **kwargs):
        return QueueNode(self, name, routing_key=routing_key, handler=handler, timeout=timeout, **kwargs)


    
class PublishNode(ControlNode):
    def __init__(self, exchange_node:ExchangeNode, routing_key, *, parameters=None, **kwargs):
        self.exchange_node = exchange_node
        self.routing_key = routing_key
        self.parameters = dict(parameters or {})
        self.kwargs = dict(kwargs)


    async def aio_set(self, value):
        if self.exchange_node.exchange is None:
            await self.exchange_node._construct()
        if self.exchange_node.exchange is None:
            raise ControlException('RabbitMQ.PublishNode.aio_set(): exchange not ready')
            
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
            content_type, content_encoding = 'text/plain', 'utf-8'
            body = body.encode()
        elif type(body) in [ list, dict ]:
            content_type, content_encoding = 'application/json', 'utf-8'
            body = json.dumps(body).encode()
        else:
            content_type, content_encoding = 'application/octet-stream', None
            if isinstance(body, (bytes, bytearray, memoryview)):
                body = bytes(body)
            elif body is None:
                body = b''
            else:
                raise ControlException(
                    f'RabbitMQ.PublishNode: body is not serializable to bytes (type={type(body).__name__})'
                )

        for k,v in self.parameters.items():
            if k not in parameters:
                parameters[k] = v
        parameters.setdefault('message_id', str(uuid.uuid4()))
        parameters.setdefault('content_type', content_type)
        if content_encoding is not None:
            parameters.setdefault('content_encoding', content_encoding)

        #set delivery_mode explicitly in **parameters of PublishNode()
        #parameters.setdefault('delivery_mode', 2)   # 1: transient, 2: persistent (needs durable=True for queue)

        message = aio_pika.Message(body, headers=headers, **parameters)
        try:
            await self.exchange_node.exchange.publish(message, self.routing_key, **self.kwargs)
        except asyncio.CancelledError:
            if self.is_stop_requested():
                return False
            else:
                raise
        except Exception as e:
            logging.error(f'RabbitMQ: publish failed (exchange={self.exchange_node.name}, key={self.routing_key}): {e}')
            raise
        
        return True

    

class QueueNode(ControlNode):
    def __init__(self, exchange_node:ExchangeNode, queue_name:str, *, routing_key:str=None, handler=None, timeout=0, **kwargs):
        self.exchange_node = exchange_node
        self.name = queue_name
        self.routing_key = routing_key or queue_name
        self.timeout = timeout
        self.kwargs = {k:v for k,v in kwargs.items()}
        
        async def _default_handler(message: aio_pika.Message) -> Message:
            parameters = {
                'message_id': message.message_id,
                'timestamp': message.timestamp,
                'content_type': message.content_type,
                'content_encoding': message.content_encoding,
                'correlation_id': message.correlation_id,
                'reply_to': message.reply_to,
            }
            headers = message.headers or {}
            content_type = message.content_type or 'application/octet-stream'
            if content_type == 'application/json':
                return Message(json.loads(message.body.decode('utf-8')), headers, parameters)
            elif content_type == 'text/plain':
                return Message(message.body.decode('utf-8'), headers, parameters)
            else:
                return Message(message.body, headers, parameters)

        self.handler = handler or _default_handler
        self.queue = None


    async def _construct(self):
        if self.queue is None:
            await self.exchange_node._construct()
            if self.exchange_node.rmq_node.channel is None:
                return  # error, retry later
            else:
                self.queue = await self.exchange_node.rmq_node.channel.declare_queue(self.name, **self.kwargs)
                await self.queue.bind(self.exchange_node.exchange, routing_key = self.routing_key)

        
    async def aio_get(self, *, selector=None):
        if self.queue is None:
            await self._construct()
        if self.queue is None:
            raise ControlException('RabbitMQ.QueueNode.aio_get(): queue not ready')

        message = None
        lapse = 0
        while True:
            try:
                message = await self.queue.get(fail=False)
            except asyncio.CancelledError:
                if self.is_stop_requested():
                    break
                else:
                    raise
            except Exception as e:
                logging.error(f'RabbitMQ: Queue.get() failed (exchange={self.exchange_node.name}, queue={self.name}): {e}')
                raise

            if message is not None and selector is not None:
                try:
                    selected = selector(message)
                except Exception:
                    await message.nack(requeue=True)
                    raise
                if not ((await selected) if inspect.isawaitable(selected) else bool(selected)):
                    await message.nack(requeue=True)
                    continue
                    
            if message is not None:
                break
            if self.is_stop_requested():
                break
            if self.timeout > 0 and lapse >= self.timeout:
                logging.warning('AMQP Queue Timeout')
                break
            
            lapse += 0.2
            try:
                await asyncio.sleep(0.2)
            except asyncio.CancelledError:
                if self.is_stop_requested():
                    break
                else:
                    raise

        if message is None:
            return Message()

        try:
            result = self.handler(message)
            if inspect.isawaitable(result):
                result = await result
            await message.ack()
        except Exception:
            await message.nack(requeue=False)
            raise
        
        return result

    
    def aio_has_data(self):
        if self.queue is None:
            return False

        channel = self.exchange_node.rmq_node.channel
        queue = channel.declare_queue(self.name, passive=True)  # returns a status for an existing queue
        return queue.declaration_result.message_count > 0
        

    # rabbitmq().direct_exchange(name).rpc_function(name, function)
    def rpc_function(self, function):
        return RpcFunctionNode(self, function)

    # rabbitmq().direct_exchange(name).queue(name).rpc_call(routing_key)
    def rpc_call(self, routing_key:str, body=None, headers=None, parameters=None):
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
    def __init__(self, queue_node:QueueNode, routing_key:str, body=None, headers=None, parameters=None):
        self.queue_node = queue_node
        self.routing_key = routing_key
        self.body = body or {}
        self.headers = headers or {}
        self.parameters = parameters or {}

        
    async def aio_get(self):
        publish_node = self.queue_node.exchange_node.publish(routing_key=self.routing_key)
        correlation_id = str(uuid.uuid4())
        parameters = dict(self.parameters)
        parameters['reply_to'] = self.queue_node.routing_key
        parameters['correlation_id'] = correlation_id
        await publish_node.aio_set((self.body, self.headers, parameters))
        
        # BUG: there might be multiple reply messages (e.g., by topic/fanout exchange)
        reply_selector = lambda message: message.correlation_id == correlation_id
        return await self.queue_node.aio_get(selector=reply_selector)
