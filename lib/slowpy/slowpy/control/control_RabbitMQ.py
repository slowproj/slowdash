# Created by Sanshiro Enomoto on 12 October 2025 #

### THIS IS NOT THREAD SAFE as pika is not ####

from slowpy.control import ControlNode, ControlException
import time, uuid, json, typing, inspect, logging
import pika


class Message:
    def __init__(
        body: dict[str,typing.Any] | str | bytes | None = None,
        headers: dict[str, typing.Any] = {},
        parameters: dict[str, typing.Any] = {}
    ):
        self.body = body
        self.headers = dict(headers)
        self.parameters = dict(parameters)
    

        
class _IncomingMessage:
    def __init__(self, ch: pika.adapters.blocking_connection.BlockingChannel, method, props: pika.BasicProperties, body: bytes):
        self._ch = ch
        self._tag = method.delivery_tag
        self.body = body
        self.headers = (props.headers or {})
        
        # parameters
        self.message_id = props.message_id
        self.timestamp = props.timestamp
        self.content_type = props.content_type
        self.content_encoding = props.content_encoding
        self.correlation_id = props.correlation_id
        self.reply_to = props.reply_to

    def ack(self):
        self._ch.basic_ack(self._tag)

    def nack(self, requeue: bool = True):
        self._ch.basic_nack(self._tag, requeue=requeue)


        
class RabbitMQNode(ControlNode):
    def __init__(self, url: str, *, qos_prefetch_count=32, heartbeat=30, timeout=300):
        self.url = url
        self.prefetch_count = qos_prefetch_count
        self.heartbeat = heartbeat
        self.timeout = timeout

        self.connection: pika.BlockingConnection | None = None
        self.channel: pika.adapters.blocking_connection.BlockingChannel | None = None
        
        self.is_retry = False
        self.last_check_time = 0

    
    def __del__(self):
        self.close()

        
    def close(self):
        if self.channel is not None:
            try:
                logging.info('RabbitMQ: closing channel')
                self.channel.close()
            except Exception as e:
                logging.info('RabbitMQ: error during closing channel: {e}')
            finally:
                self.channel = None
            
        if self.connection is not None:
            try:
                logging.info('RabbitMQ: closing connection')
                self.connection.close()
            except Exception as e:
                logging.info('RabbitMQ: error during closing connection: {e}')
            finally:
                self.connection = None
            
        self.is_retry = False
        self.last_check_time = 0

            
    def _construct(self):
        if self.channel is None:
            if self.is_retry:
                logging.info(f'RabbitMQ: retrying to connect to {self.url}')
            try:
                params = pika.URLParameters(self.url)
                params.heartbeat = self.heartbeat
                params.blocked_connection_timeout = self.timeout
                self.connection = pika.BlockingConnection(params)
                self.channel = self.connection.channel()
                self.is_retry = False
                self.last_check_time = time.monotonic()
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
                self.channel.basic_qos(prefetch_count=self.prefetch_count)
            except Exception as e:
                logging.warning(f'RabbitMQ: unable to set QoS prefetch count ({self.prefetch_count}): {e}')


    def _check_connection(self):
        if self.connection is None:
            return False
        if self.channel is None:
            try:
                self.connection.close()
            except:
                pass
            self.connection = None
            return False

        now = time.monotonic()
        if now - self.last_check_time < self.heartbeat-10:
            return True
        
        if self.connection.is_closed or self.channel.is_closed:
            logging.warning(f'RabbitMQ: stream closed')

        else:
            try:
                self.channel.basic_get(queue='__slowdash_check_sacrifice', auto_ack=True)
            except (pika.exceptions.StreamLostError, pika.exceptions.ChannelClosedByBroker) as e:
                logging.warning(f'RabbitMQ: stream lost: {e}')
            except:
                # not a stream error -> connection is ok (expect an error for reading from an non-existing queue)
                self.last_check_time = now
                return True
            
        try:
            self.connection.close()
        except:
            pass
        
        self.channel = None
        self.connection = None

        return False
    
                
    ## child nodes ##
    # rabbitmq().direct_exchange(name, **kwargs)
    def direct_exchange(self, name: str, **kwargs):
        return ExchangeNode(self, 'direct', name, **kwargs)

    
    # rabbitmq().topic_exchange(name, **kwargs)
    def topic_exchange(self, name: str, **kwargs):
        return ExchangeNode(self, 'topic', name, **kwargs)

    
    # rabbitmq().fanout_exchange(name, **kwargs)
    def fanout_exchange(self, name: str, **kwargs):
        return ExchangeNode(self, 'fanout', name, **kwargs)

    
    @classmethod
    def _node_creator_method(cls):
        def rabbitmq(self, url: str, **kwargs):
            if True:
                return RabbitMQNode(url, **kwargs)
                
            try:
                self._rmq_nodes.keys()
            except Exception:
                self._rmq_nodes = {}
            node = self._rmq_nodes.get(url)
            if node is None:
                node = RabbitMQNode(url, **kwargs)
                self._rmq_nodes[url] = node
            return node
        return rabbitmq


    
class ExchangeNode(ControlNode):
    def __init__(self, rmq_node:RabbitMQNode, exchange_type:str, name:str, **kwargs):
        self.rmq_node = rmq_node
        self.exchange_type = exchange_type  # 'direct' | 'topic' | 'fanout'
        self.name = name
        self.kwargs = dict(kwargs)
        
        self._declared = False

        
    def _construct(self):
        if not self._declared or self.rmq_node.channel is None:
            if self.rmq_node.channel is None:
                self.rmq_node._construct()
            if self.rmq_node.channel is None:
                return  # retry later
            
            try:
                self.rmq_node.channel.exchange_declare(
                    exchange = self.name,
                    exchange_type = self.exchange_type,
                    **self.kwargs
                )
                self._declared = True
            except Exception as e:
                logging.error(f'failed to declare exchange {self.name}: {e}')
                self._declared = False  # retry later
                

    ## child nodes ##
    # rabbitmq().XXX_exchange(name).publish(routing_key:str)
    def publish(self, routing_key: str, *, parameters=None, **kwargs):
        return PublishNode(self, routing_key, parameters=parameters, **kwargs)

    # rabbitmq().XXX_exchange(name).queue(name, routing_key, **kwargs)
    def queue(self, name: str, *, routing_key: str | None = None, handler=None, timeout=0, **kwargs):
        return QueueNode(self, name, routing_key=routing_key, handler=handler, timeout=timeout, **kwargs)
    
    

class PublishNode(ControlNode):
    def __init__(self, exchange_node: ExchangeNode, routing_key, *, parameters=None, **kwargs):
        self.exchange_node = exchange_node
        self.routing_key = routing_key
        self.parameters = dict(parameters or {})
        self.kwargs = dict(kwargs)

        
    def set(self, value):
        self.exchange_node.rmq_node._check_connection()
        if not self.exchange_node._declared or self.exchange_node.rmq_node.channel is None:
            self.exchange_node._construct()
        if not self.exchange_node._declared or self.exchange_node.rmq_node.channel is None:
            raise ControlException('RabbitMQ.PublishNode.set(): exchange not ready')

        body, headers, parameters = ({}, {}, {})
        if isinstance(value, Message):
            body, headers, parameters = value
        elif isinstance(value, tuple):
            if len(value) == 1:
                (body,) = value
            elif len(value) == 2:
                body, headers = value
            elif len(value) == 3:
                body, headers, parameters = value
        else:
            body = value

        if isinstance(body, str):
            content_type, content_encoding = 'text/plain', 'utf-8'
            body = body.encode()
        elif isinstance(body, (list, dict)):
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

        props = pika.BasicProperties(
            message_id = parameters.get('message_id'),
            timestamp = parameters.get('timestamp'),
            content_type = parameters.get('content_type'),
            content_encoding = parameters.get('content_encoding'),
            correlation_id = parameters.get('correlation_id'),
            reply_to = parameters.get('reply_to'),
            headers = headers or {},
            delivery_mode = parameters.get('delivery_mode'),
        )

        channel = self.exchange_node.rmq_node.channel
        try:
            channel.basic_publish(
                exchange = self.exchange_node.name,
                routing_key = self.routing_key,
                body = body,
                properties = props,
                **self.kwargs
            )
        except (pika.exceptions.StreamLostError, pika.exceptions.ChannelClosedByBroker) as e:
            logging.warning(f'RabbitMQ: stream lost (basic_publish()): {e}')
            try:
                self.exchange_node.rmq_node.connection.close()
            except:
                pass
            self.exchange_node.rmq_node.channel = None
            self.exchange_node.rmq_node.connection = None
            return False

        except Exception as e:
            logging.error(f'RabbitMQ: publish failed (exchange={self.exchange_node.name}, key={self.routing_key}): {e}')
            raise
        
        return True

    

class QueueNode(ControlNode):
    def __init__(self, exchange_node:ExchangeNode, queue_name:str, *, routing_key:list[str]|str|None=None, handler=None, timeout:float=0, **kwargs):
        self.exchange_node = exchange_node
        self.name = queue_name
        self.timeout = timeout
        self.kwargs = {k:v for k,v in kwargs.items()}

        if type(routing_key) is list:
            self.routing_keys = routing_key
        else:
            self.routing_keys = [ routing_key or queue_name ]
        
        def _default_handler(incoming: _IncomingMessage) -> Message:
            parameters = {
                'message_id': incoming.message_id,
                'timestamp': incoming.timestamp,
                'content_type': incoming.content_type,
                'content_encoding': incoming.content_encoding,
                'correlation_id': incoming.correlation_id,
                'reply_to': incoming.reply_to,
            }
            headers = incoming.headers or {}
            content_type = incoming.content_type or 'application/octet-stream'
            if content_type == 'application/json':
                return Message(json.loads(incoming.body.decode('utf-8')), headers, parameters)
            elif content_type == 'text/plain':
                return Message(incoming.body.decode('utf-8'), headers, parameters)
            else:
                return Message(incoming.body, headers, parameters)

        self.handler = handler or _default_handler
        
        self._declared = False

        
    def _construct(self):
        if not self._declared or self.exchange_node.rmq_node.channel is None:
            self.exchange_node._construct()
            channel = self.exchange_node.rmq_node.channel
            if channel is None:
                return  # retry later
            
            try:
                channel.queue_declare(queue=self.name, **self.kwargs)
                for key in self.routing_keys:
                    channel.queue_bind(queue=self.name, exchange=self.exchange_node.name, routing_key=key)
                self._declared = True
            except Exception as e:
                logging.error(f'failed to declare/bind queue {self.name}: {e}')
                self._declared = False
                

    def get(self, *, selector=None):
        self.exchange_node.rmq_node._check_connection()
        if not self._declared or self.exchange_node.rmq_node.channel is None:
            self._construct()
        if not self._declared or self.exchange_node.rmq_node.channel is None:
            raise ControlException('RabbitMQ.QueueNode.get(): queue not ready')

        message: _IncomingMessage | None = None
        channel = self.exchange_node.rmq_node.channel
        lapse = 0
        while True:
            try:
                method, props, body = channel.basic_get(queue=self.name, auto_ack=False)
            except (pika.exceptions.StreamLostError, pika.exceptions.ChannelClosedByBroker) as e:
                logging.warning(f'RabbitMQ: stream lost (basic_get()): {e}')
                try:
                    self.exchange_node.rmq_node.connection.close()
                except:
                    pass
                self.exchange_node.rmq_node.channel = None
                self.exchange_node.rmq_node.connection = None
                break                
            except Exception as e:
                logging.error(f'RabbitMQ: basic_get failed (exchange={self.exchange_node.name}, queue={self.name}): {e}')
                raise

            if method:
                message = _IncomingMessage(channel, method, props or pika.BasicProperties(), body or b'')
                if selector is not None:
                    try:
                        selected = selector(message)
                        if inspect.isawaitable(selected):
                            raise ControlException('RabbitMQ: async selector cannot be used in No-Async RabbitMQ')
                    except Exception:
                        message.nack(requeue=True)
                        raise
                    if not selected:
                        message.nack(requeue=True)
                        continue

            if message is not None:
                break
            if self.is_stop_requested():
                break
            if self.timeout > 0 and lapse >= self.timeout:
                logging.warning('AMQP Queue Timeout')
                break

            lapse += 0.2
            time.sleep(0.2)

        if message is None:
            return Message()

        try:
            result = self.handler(message)
            if inspect.isawaitable(result):
                raise ControlException('RabbitMQ: async handler cannot be used in No-Async RabbitMQ')
            message.ack()
        except Exception:
            message.nack(requeue=False)
            raise

        return result


    def has_data(self):
        if not self._declared:
            return False

        channel = self.exchange_node.rmq_node.channel
        status = channel.queue_declare(queue=self.name, passive=True)  # returns a status for an existing queue
        return status.method.message_count > 0
        
        
    # rabbitmq().direct_exchange(name).rpc_function(name, function)
    def rpc_function(self, function):
        return RpcFunctionNode(self, function)

    # rabbitmq().direct_exchange(name).queue(name).rpc_call(routing_key)
    def rpc_call(self, routing_key: str, body=None, headers=None, parameters=None):
        return RpcCallNode(self, routing_key, body, headers, parameters)

    

class RpcFunctionNode(ControlNode):
    def __init__(self, queue_node: QueueNode, function):
        self.queue_node = queue_node
        self.function = function

        
    def get(self):
        request_message = self.queue_node.get()
        if request_message.body is None:
            return None

        if inspect.iscoroutinefunction(self.function):
            raise ControlException('RabbitMQ: async rpc_function cannot be used in No-Async RabbitMQ')
        return_value = self.function(request_message)

        routing_key = request_message.parameters.get('reply_to', None)
        if routing_key is not None:
            parameters = {
                'correlation_id': request_message.parameters.get('correlation_id', None),
            }
            publish_node = self.queue_node.exchange_node.publish(routing_key, parameters=parameters)
            publish_node.set(return_value)

        return return_value


    
class RpcCallNode(ControlNode):
    def __init__(self, queue_node: QueueNode, routing_key: str, body=None, headers=None, parameters=None):
        self.queue_node = queue_node
        self.routing_key = routing_key
        self.body = body or {}
        self.headers = headers or {}
        self.parameters = parameters or {}

        
    def get(self):
        publish_node = self.queue_node.exchange_node.publish(routing_key=self.routing_key)
        correlation_id = str(uuid.uuid4())
        parameters = dict(self.parameters)
        parameters['reply_to'] = self.queue_node.routing_keys[0]
        parameters['correlation_id'] = correlation_id
        publish_node.set((self.body, self.headers, parameters))

        # BUG: there might be multiple reply messages (e.g., by topic/fanout exchange)
        reply_selector = lambda m: m.correlation_id == correlation_id
        return self.queue_node.get(selector=reply_selector)
