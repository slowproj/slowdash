# Created by Sanshiro Enomoto on 23 March 2026 #

import os, time, re, uuid, socket, asyncio, inspect, logging
from urllib.parse import urlsplit
from functools import wraps
from slowpy.control import control_system as ctrl


class Mesh:
    _mesh_sequence_id = 0
    
    def __init__(self,
        url: str|None = None,
        *,
        name: str|None = None,
        rpc_timeout: float = 10,
        loop_timeout: float = 0.1,
        sep: str|None = '.',
        single_wc: str|None = '*',
        tail_wc: str|None = '>',
        rpc_file_prefix: str|None = None
    ):
        self.loop_timeout = loop_timeout
        self.rpc_timeout = rpc_timeout

        self.sep_mesh = sep
        self.single_wc_mesh = single_wc
        self.tail_wc_mesh = tail_wc
        
        self.sep = sep
        self.single_wc = single_wc
        self.tail_wc = tail_wc
        self.pubargs = {}
        self.subargs = { 'timeout': self.loop_timeout }
        
        if url is not None:
            self.connect(url)
        else:
            self.pubsub = ctrl.import_control_module('AsyncLocalPubsub').async_localpubsub()

        if name is None:
            self.name = os.path.splitext(os.path.basename(inspect.stack()[1].filename))[0]
            if rpc_file_prefix is not None:
                if self.name.startswith(rpc_file_prefix):
                    self.name = self.name[len(rpc_file_prefix):]
            self.name = re.sub(r'[^a-zA-Z0-9]', '_', self.name)
        else:
            self.name = name

        Mesh._mesh_sequence_id += 1
        self.mesh_id = f'{self.name}_HOST_{socket.gethostname()}_PID_{os.getpid()}_SEQ_{Mesh._mesh_sequence_id}'
        self.mesh_id = re.sub(r'[^a-zA-Z0-9]', '_', self.mesh_id)
        self.rpc_count = 0
        self.reply_queues = {}  # CorrelationID(str) -> asyncio.Queue
        self.reply_lock = asyncio.Lock()
        
        self.callback_coros = []
        self.callback_coros.append(self._start_rpc_call_handler())
        self.callback_coros.append(self._start_rpc_reply_handler())
        self.callback_tasks = set()

        self.function_table = {}  # FunctionName:str -> function
        
        
    def connect(self, url:str):
        if url is None:
            return
        
        try:
            o = urlsplit(url)
            if o.scheme in ['slowmq', 'slowdash']:
                self.pubsub = ctrl.import_control_module('AsyncSlowMQ').async_slowmq(f'slowmq://{o.netloc}')
                self.sep, self.single_wc, self.tail_wc = tail_wc = '.', '*', '>'
            elif o.scheme == 'nats':
                self.pubsub = ctrl.import_control_module('AsyncNATS').async_nats(url)
                self.sep, self.single_wc, self.tail_wc = tail_wc = '.', '*', '>'
            elif o.scheme == 'mqtt':
                self.pubsub = ctrl.import_control_module('AsyncMQTT').async_mqtt(o.hostname, o.port or 1883)
                self.sep, self.single_wc, self.tail_wc = tail_wc = '/', '+', '#'
            elif o.scheme == 'redis':
                self.pubsub = ctrl.import_control_module('AsyncRedis').async_redis(url)
                self.sep, self.single_wc, self.tail_wc = tail_wc = ':', '*', '*'
            elif o.scheme in ['amqp', 'rabbitmq', 'rmq']:
                amqp = ctrl.import_control_module('AsyncRabbitMQ').async_rabbitmq(f'amqp://{o.netloc}')
                if len(o.path) > 1:
                    self.pubsub = amqp.topic_exchange(o.path[1:])
                else:
                    logging.error('Mesh: AMQP (RabbitMQ) requries an exchange name')
                self.sep, self.single_wc, self.tail_wc = tail_wc = '.', '*', '#'
            else:
                logging.error('Mesh: unknown pubsub type: %s' % scheme)
        except Exception as e:
            logging.error(e)

            
    def _convert_topic(self, topic:str):
        converted = topic
        
        if self.sep_mesh is not None and self.sep_mesh != self.sep:
            if topic.count(self.sep):
                logging.warning(f'Mesh: Separator char "{self.sep}" is used in topic "{topic}"')
            converted = converted.replace(self.sep_mesh, self.sep)
            
        if self.single_wc_mesh is not None and self.single_wc_mesh != self.single_wc:
            converted = converted.replace(self.single_wc_mesh, self.single_wc)
            if topic.count(self.single_wc):
                logging.warning(f'Mesh: Wildcard char "{self.single_wc}" is used in topic "{topic}"')
            
        if self.tail_wc_mesh is not None and self.tail_wc_mesh != self.tail_wc:
            converted = converted.replace(self.tail_wc_mesh, self.tail_wc)
            if topic.count(self.tail_wc):
                logging.warning(f'Mesh: Wildcard char "{self.tail_wc}" is used in topic "{topic}"')

        return converted

            
    async def aio_close(self):
        await self.aio_stop()
        try:
            await self.pubsub.aio_close()
        except:
            pass
            
            
    async def aio_start(self):
        """ start async tasks to handle subscription and RPC messages
        - This function (await aio_start()) returns immediately without blocking.
        - The created tasks can be stopped by aio_stop().
        """
        
        await self.aio_stop()

        for coro in self.callback_coros:
            task = asyncio.create_task(coro)
            task.add_done_callback(self.callback_tasks.discard)
            self.callback_tasks.add(task)

        
    async def aio_stop(self):
        while self.callback_tasks:
            task = self.callback_tasks.pop()
            try:
                task.cancel()
                await task
            except Exception as e:
                logging.error(f'Mesh: error during clean up: {e}')
            except:
                pass


    def publisher(self, topic:str):
        return self.pubsub.publisher(self._convert_topic(topic), **self.pubargs).json()


    def subscriber(self, topic:str):
        return self.pubsub.subscriber(self._convert_topic(topic), **self.subargs).json()


    async def aio_publish(self, topic:str, value, *, headers:dict|None=None):
        return await self.publisher(topic).headers(headers or {}).aio_set(value)


    async def aio_call(self, name:str, *args, **kwargs):
        reply = await self.aio_call_many(name, list(args), dict(kwargs), multiple_replies=False)
        if reply.get('status') == 'ok':
            return reply.get('return_value')
        else:
            raise Exception(f'Mesh: RPC remote error: {name}: {reply.message}')
    
        
    async def aio_call_many(self, name:str, args:list, kwargs:dict, *, multiple_replies=True, timeout=None):
        if len(name) == 0:
            return
        name = re.sub(r'[^a-zA-Z0-9\.]', '_', name)
        self.rpc_count += 1
        
        dots = name.count('.')
        if dots == 0:
            module_name = '__broadcast'  # not implemented yet (no receiver subscription)
            function_name = name
            reply_to = None
        else:
            module_name, function_name = name.split('.', 1)
            reply_to = self.sep_mesh.join(['rpc_reply', self.mesh_id])
        topic = self.sep_mesh.join(['rpc', module_name])
        correlation_id = str(self.rpc_count)  # NATS can handle only str in headers...
        headers = {
            'sender': self.name,
            'sender_id': self.mesh_id,
            'reply_to': reply_to,
            'correlation_id': correlation_id,
            'message_id': str(uuid.uuid4()),
            'module': module_name,
            'function': function_name,
        }
        body = {
            'args': args,
            'kwargs': kwargs
        }

        reply_queue = asyncio.Queue()
        self.reply_queues[correlation_id] = reply_queue
        
        await self.aio_publish(topic, body, headers=headers)

        replies = []
        start = time.monotonic()
        end = start + (timeout or self.rpc_timeout)
        while not ctrl.is_stop_requested():
            try:
                replies.append(await asyncio.wait_for(reply_queue.get(), timeout=self.loop_timeout))
                if not multiple_replies:
                    break
            except (asyncio.TimeoutError, asyncio.QueueEmpty):
                pass
            now = time.monotonic()
            if now > end:
                if len(replies) == 0:
                    logging.warning(f'Mesh: RPC timeout: {name}()')
                break

        async with self.reply_lock:
            del self.reply_queues[correlation_id]

        if multiple_replies:
            return replies
        elif len(replies) > 0:
            return replies[0]
        else:
            return None

        
    def export(self, func):
        """decorator to mark the function mesh-callable
        """
        self.function_table[func.__name__] = func
        @wraps(func)
        def wrapper(*args, **argv):
            return func(*args, **argv)
        return wrapper


    async def _start_rpc_call_handler(self):
        topic = self.sep_mesh.join(['rpc', self.name])
        subscriber = self.subscriber(topic)
        try:
            while not ctrl.is_stop_requested():
                headers, data = await subscriber.aio_get()
                if data is None:
                    continue
                result = await self._execute_rpc_function(
                    headers.get('function'), *data.get('args',[]), **data.get('kwargs',{})
                )
                reply_to = headers.get('reply_to')
                if reply_to is not None:
                    reply_headers = { k:v for k,v in headers.items() if k not in ['topic', 'reply_to', 'message_id'] }
                    reply_headers.update({
                        'sender': self.name,
                        'sender_id': self.mesh_id,
                        'message_id': str(uuid.uuid4()),
                    })
                    await self.aio_publish(reply_to, result, headers=reply_headers)
        except Exception as e:
            logging.error(f'Mesh: rpc_call_handler: {e}')
        except:
            pass
    

    async def _start_rpc_reply_handler(self):
        topic = self.sep_mesh.join(['rpc_reply', self.mesh_id])
        subscriber = self.subscriber(topic)
        try:
            while not ctrl.is_stop_requested():
                headers, data = await subscriber.aio_get()
                if data is None:
                    continue
                logging.debug(f'Mesh: RPC Reply: {data}')
                correlation_id = headers.get('correlation_id', "NONE")
                async with self.reply_lock:
                    queue = self.reply_queues.get(correlation_id, None)
                    if queue is not None:
                        await queue.put(data)
                    else:
                        rpc_name = f"{headers.get('module')}.{headers.get('function')}()"
                        logging.warning(f'RPC reply not processed: received multiple replies or the reply is too late: {rpc_name}')
        except Exception as e:
            logging.error(f'Mesh: rpc_reply_handler: {e}')
        except:
            pass

        
    async def _execute_rpc_function(self, function_name:str, *args, **kwargs):
        logging.debug(f'Mesh: RPC Call: {function_name}({args}, {kwargs})')
        
        func = self.function_table.get(function_name)
        if func is None:
            return { 'status': 'error', 'message': f'no such function: {function_name}', 'return_value': None }
        
        try:
            result = func(*args, **kwargs)
            if asyncio.iscoroutine(result):
                result = await result
            return { 'status': 'ok', 'message': 'ok', 'return_value': result }
        except Exception as e:
            return { 'status': 'error', 'message': str(e), 'return_value': None }
        except asyncio.CancelledError:
            return { 'status': 'cancelled', 'message': 'cancelled', 'return_value': None }
        except:
            return { 'status': 'error', 'message': 'other errors', 'return_value': None }
