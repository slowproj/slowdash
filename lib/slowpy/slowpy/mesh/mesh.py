# Created by Sanshiro Enomoto on 23 March 2026 #

import os, time, re, uuid, socket, threading, asyncio, inspect, logging
from typing import Any
from collections.abc import Callable
from urllib.parse import urlsplit
from slowpy.control import ControlNode, control_system as ctrl


class Mesh:
    _mesh_sequence_id = 0
    
    def __init__(self,
        url: str|None = None,
        *,
        name: str|None = None,
        on_reconnect: Callable[[],None] = None,
        rpc_timeout: float = 5,
        loop_timeout: float = 0.1,
        sep: str|None = '.',
        single_wc: str|None = '*',
        tail_wc: str|None = '>',
        name_prefix_to_drop: str|None = None
    ):
        self._on_reconnect = on_reconnect
        self._loop_timeout = loop_timeout
        self._rpc_timeout = rpc_timeout
        self._name_prefix_to_drop = name_prefix_to_drop

        self._sep_mesh = sep
        self._single_wc_mesh = single_wc
        self._tail_wc_mesh = tail_wc
        
        self._sep = sep
        self._single_wc = single_wc
        self._tail_wc = tail_wc
        self._pubargs = {}
        self._subargs = { 'timeout': self._loop_timeout }
        
        self._name = name
        self._mesh_id = None
        self._is_running = False
        
        self._rpc_count = 0
        self._reply_queues = {}  # CorrelationID(str) -> asyncio.Queue
        self._reply_lock = asyncio.Lock()
        
        self._subscription_coros = []
        self._callback_tasks = set()

        self._function_table = {  # FunctionName:str -> function
            '_sd_node_call': self.node_call
        }

        self._exported_nodes = {}

        self._registry = Registry(self)
        
        if url is not None:
            self.connect(url, name)
        else:
            self._pubsub = ctrl.import_control_module('AsyncLocalPubsub').async_localpubsub()

        
    def connect(self, url:str, name:str|None=None):
        if url is None:
            return

        if name is not None:
            self._name = name
        elif self._name is None:
            self._name = os.path.splitext(os.path.basename(inspect.stack()[-1].filename))[0]
            if self._name_prefix_to_drop is not None:
                if self._name.startswith(self._name_prefix_to_drop):
                    self._name = self._name[len(self._name_prefix_to_drop):]
            self._name = re.sub(r'[^a-zA-Z0-9]', '_', self._name)

        if self._mesh_id is None:
            Mesh._mesh_sequence_id += 1
            self._mesh_id = f'{self._name}_{socket.gethostname()}_{os.getpid()}_{Mesh._mesh_sequence_id}'
            self._mesh_id = re.sub(r'[^a-zA-Z0-9]', '_', self._mesh_id)
        
        try:
            o = urlsplit(url)
            if o.scheme in ['slowmq', 'slowdash']:
                self._pubsub = ctrl.import_control_module('AsyncSlowMQ').async_slowmq(
                    f'slowmq://{o.netloc}', name=self._mesh_id, on_reconnect=self._on_reconnect
                )
                self._sep, self._single_wc, self._tail_wc = tail_wc = '.', '*', '>'
            elif o.scheme in ['slowmqs', 'slowdashs']:
                self._pubsub = ctrl.import_control_module('AsyncSlowMQ').async_slowmq(
                    f'slowmqs://{o.netloc}', name=self._mesh_id, on_reconnect=self._on_reconnect
                )
                self._sep, self._single_wc, self._tail_wc = tail_wc = '.', '*', '>'
            elif o.scheme == 'nats':
                self._pubsub = ctrl.import_control_module('AsyncNATS').async_nats(url)
                self._sep, self._single_wc, self._tail_wc = tail_wc = '.', '*', '>'
            elif o.scheme == 'mqtt':
                self._pubsub = ctrl.import_control_module('AsyncMQTT').async_mqtt(o.hostname, o.port or 1883)
                self._sep, self._single_wc, self._tail_wc = tail_wc = '/', '+', '#'
            elif o.scheme == 'redis':
                self._pubsub = ctrl.import_control_module('AsyncRedis').async_redis(url)
                self._sep, self._single_wc, self._tail_wc = tail_wc = ':', '*', '*'
            elif o.scheme in ['amqp', 'rabbitmq', 'rmq']:
                amqp = ctrl.import_control_module('AsyncRabbitMQ').async_rabbitmq(f'amqp://{o.netloc}')
                if len(o.path) > 1:
                    self._pubsub = amqp.topic_exchange(o.path[1:])
                else:
                    logging.error('Mesh: AMQP (RabbitMQ) requries an exchange name')
                self._sep, self._single_wc, self._tail_wc = tail_wc = '.', '*', '#'
            else:
                self._pubsub = ctrl.import_control_module('AsyncLocalPubsub').async_localpubsub()
                logging.error(f'Mesh: unknown pubsub type: {o.scheme}')
        except Exception as e:
            self._pubsub = ctrl.import_control_module('AsyncLocalPubsub').async_localpubsub()
            logging.error(e)


    @property
    def name(self):
        return self._name
    
            
    @property
    def mesh_id(self):
        return self._mesh_id
    
            
    @property
    def registry(self):
        return self._registry
    
            
    def export_functions(self):
        return { name:func for name,func in self._function_table.items() if not name.startswith('_sd_') }

    
    def export_variables(self):
        return self._exported_nodes

    
    def _convert_topic(self, topic:str):
        converted = topic
        
        if self._sep_mesh is not None and self._sep_mesh != self._sep:
            if topic.count(self._sep):
                logging.warning(f'Mesh: Separator char "{self._sep}" is used in topic "{topic}"')
            converted = converted.replace(self._sep_mesh, self._sep)
            
        if self._single_wc_mesh is not None and self._single_wc_mesh != self._single_wc:
            converted = converted.replace(self._single_wc_mesh, self._single_wc)
            if topic.count(self._single_wc):
                logging.warning(f'Mesh: Wildcard char "{self._single_wc}" is used in topic "{topic}"')
            
        if self._tail_wc_mesh is not None and self._tail_wc_mesh != self._tail_wc:
            converted = converted.replace(self._tail_wc_mesh, self._tail_wc)
            if topic.count(self._tail_wc):
                logging.warning(f'Mesh: Wildcard char "{self._tail_wc}" is used in topic "{topic}"')

        return converted

            
    async def aio_close(self):
        await self.aio_stop()
        try:
            await self._pubsub.aio_close()
        except:
            pass
            
            
    async def aio_start(self):
        """ start async tasks to handle subscription and RPC messages
        - This function (await aio_start()) returns immediately without blocking.
        - The created tasks can be stopped by aio_stop().
        """
        
        if self._mesh_id is None:
            logging.error('Mesh not connected')
            return
                
        await self.aio_stop()
        self._is_running = True

        await self._start_coro(self._start_rpc_call_handler())
        await self._start_coro(self._start_rpc_reply_handler())
        
        for coro in self._subscription_coros:
            await self._start_coro(coro)

        
    async def _start_coro(self, coro):
        task = asyncio.create_task(coro)
        task.add_done_callback(self._callback_tasks.discard)
        self._callback_tasks.add(task)
        
        
    async def aio_stop(self):
        self._is_running = False
        while self._callback_tasks:
            task = self._callback_tasks.pop()
            try:
                task.cancel()
                await task
            except Exception as e:
                logging.error(f'Mesh: error during clean up: {e}')
            except:
                pass


    def publisher(self, topic:str):
        '''async-set type publisher (control node)
        '''
        return self._pubsub.publisher(self._convert_topic(topic), **self._pubargs).json()


    def subscriber(self, topic:str):
        '''async-get type subscription (control node)
        '''
        return self._pubsub.subscriber(self._convert_topic(topic), **self._subargs).json()


    async def aio_publish(self, topic:str, value, *, headers:dict|None=None):
        '''direct publish
        '''
        if isinstance(value, MeshPacket):
            h, b = value.pack()
            return await self.publisher(topic).headers(h).aio_set(b)
    
        return await self.publisher(topic).headers(headers or {}).aio_set(value)

    
    def publish(self, topic:str, value, *, headers:dict|None=None):
        '''no-async direct publish; this needs an eventloop somewhere
        '''
        loop = asyncio.get_running_loop()
        loop.create_task(self.aio_publish(topic, value, headers=headers))

    
    async def aio_subscribe(self, topic:str, func):
        '''callback type subscription
        '''
        coro = self._add_subscription_callback(func, topic)
        if self._is_running:
            await self._start_coro(coro)


    async def aio_call(self, name:str, *args, **kwargs):
        try:
            reply = await self.aio_call_many(name, list(args), dict(kwargs), expected_replies=1, raise_on_timeout=True)
        except Exception as e:
            raise e
        
        if len(reply) != 1:
            raise Exception(f'Mesh: RPC error: {name}: no reply')
        if reply[0].get('status').lower() != 'ok':
            raise Exception(f'Mesh: RPC remote error: {name}: {reply[0].get("message")}')
        
        return reply[0].get('return_value')
    
        
    async def aio_call_many(self, name:str, args:list, kwargs:dict, *, expected_replies:int|None=None, timeout:float|None=None, raise_on_timeout:bool=False):
        """ invokes a RPC call which might be received by multiple PRC handlers
        Arguments:
          - name (str): name of the remote function, "{module_name}.{function_name}"
          - args (list[Any]): ordered argments
          - kwargs (dict[str,Any]): keyword argments
          - expected_replies (int|None): the number of expected replies, None for unknown/unlimited (controlled by timeout)
          - timeout (float|None): maximum time to wait for replies, None for the default Mesh-global RPC timeout        
          - raise_on_timeout (bool): if True, an exception will be raised; otherwise, will return a shorter repliy list
        Return Value (list[dict[str,Any]]): list of replies
        """
        
        if self._mesh_id is None:
            raise Exception(f'Mesh: RPC error: Mesh not connected')
        
        if len(name) == 0:
            if raise_on_timeout:
                raise Exception(f'Mesh: RPC timeout: empty RPC name: {name}()')
            else:
                return []
        
        name = re.sub(r'[^a-zA-Z0-9\.]', '_', name)
        self._rpc_count += 1
        
        dots = name.count('.')
        if dots == 0:
            module_name = '__broadcast'  # not implemented yet (no receiver subscription)
            function_name = name
            reply_to = None
        else:
            module_name, function_name = name.rsplit('.', 1)
            reply_to = self._sep_mesh.join(['sd.rpc_reply', self._mesh_id])
        topic = self._sep_mesh.join(['sd.rpc', module_name])
        correlation_id = str(self._rpc_count)  # NATS can handle only str in headers...
        headers = {
            'sender': self._name,
            'sender_id': self._mesh_id,
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
        self._reply_queues[correlation_id] = reply_queue

        try:
            await self.aio_publish(topic, body, headers=headers)

            replies = []
            start = time.monotonic()
            end = start + (timeout or self._rpc_timeout)
            while not ctrl.is_stop_requested():
                try:
                    replies.append(await asyncio.wait_for(reply_queue.get(), timeout=self._loop_timeout))
                    if expected_replies is not None and len(replies) >= expected_replies:
                        break
                except (asyncio.TimeoutError, asyncio.QueueEmpty):
                    pass
                now = time.monotonic()
                if now > end:
                    if expected_replies is not None and len(replies) < expected_replies:
                        logging.warning(f'Mesh: RPC timeout: {name}()')
                        if raise_on_timeout:
                            raise Exception(f'Mesh: RPC timeout: {name}()')
                    break

        finally:
            async with self._reply_lock:
                del self._reply_queues[correlation_id]

        return replies


    async def node_call(self, *argc, **argv):
        node_name = argv.get('node_name')
        method = argv.get('method')
        node = self._exported_nodes.get(node_name)
        if node is None:
            raise Exception(f'unknown node: "{node_name}"')

        if method == 'set':
            return await node.aio_set(argv.get('value'))
        if method == 'get':
            return await node.aio_get()
        
        raise Exception(f'bad node method: {node_name}.{method}()')

    
    def remote_node(self, name:str):
        return RemoteControlNode(self, name)
        
        
    def export(self, *args, **kwargs):
        """
        USAGE 1: decorator to mark the function mesh-callable
        USAGE 2: usual method to export a function or node
        """
        # def export(self, name:str, node:ControlNode)
        if len(args) == 2 and isinstance(args[0], str) and isinstance(args[1], ControlNode):
            name = args[0]
            node = args[1]
            self._exported_nodes[name] = node

        # def export(self, name:str, func:callable)
        elif len(args) == 2 and isinstance(args[0], str) and callable(args[1]):
            name = args[0]
            func = args[1]
            self._function_table[name] = func
            try:
                func._slowpy_task = True
            except: # func might not have a dict
                pass

        # decorator without (): e.g., @mesh.export
        elif len(args) == 1 and callable(args[0]):
            func = args[0]
            self._function_table[func.__name__] = func
            try:
                func._slowpy_task = True   
            except: # func might not have a dict
                pass
            return func
            
        # decorator with (): e.g., @mesh.export(**kwargs)
        else:
            name = kwargs.get('name')
            def wrapper(func):
                self._function_table[name or func.__name__] = func        
                func._slowpy_task = True
                return func
            return wrapper
        
        
    def on(self, topic:str):
        """decorator to make a subscriptoin message handler
        Args:
        - topic: path pattern to match
        """
        def wrapper(func):
            func._slowpy_task = True
            self._add_subscription_callback(func, topic)
            return func
        return wrapper


    def _add_subscription_callback(self, func, topic:str):
        """
        Args:
          func: callback function
          topic: topic filter
        """
        
        params = inspect.signature(func).parameters
        nargs = len(params)
        if nargs > 2:
            logging.error(f'Invalid mesh message handler: wrong number of arguments')
            return None

        async def handle_subscription():
            subscriber = self.subscriber(topic)
            try:
                while not ctrl.is_stop_requested():
                    headers, data = await subscriber.aio_get()
                    if data is None:
                        continue
                    if nargs == 0:
                        result = func()
                    elif nargs == 1:
                        p0 = [ v for v in params.values() ][0]
                        annotation = p0.annotation
                        if issubclass(annotation, MeshPacket):
                            result = func(annotation.unpack(headers, data))
                        else:
                            result = func(data)
                    elif nargs == 2:
                        result = func(headers, data)
                    if asyncio.iscoroutine(result):
                        await result
            except Exception as e:
                logging.error(f'Mesh: error in subscription callback: {func.__name__}(): {e}')

        coro = handle_subscription()
        self._subscription_coros.append(coro)

        return coro
    
                
    async def _start_rpc_call_handler(self):
        topic = self._sep_mesh.join(['sd.rpc', self._name])
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
                        'sender': self._name,
                        'sender_id': self._mesh_id,
                        'message_id': str(uuid.uuid4()),
                    })
                    await self.aio_publish(reply_to, result, headers=reply_headers)
        except Exception as e:
            logging.error(f'Mesh: rpc_call_handler: {e}')
        except:
            pass
    

    async def _start_rpc_reply_handler(self):
        topic = self._sep_mesh.join(['sd.rpc_reply', self._mesh_id])
        subscriber = self.subscriber(topic)
        try:
            while not ctrl.is_stop_requested():
                headers, data = await subscriber.aio_get()
                if data is None:
                    continue
                logging.debug(f'Mesh: RPC Reply: {data}')
                correlation_id = headers.get('correlation_id', "NONE")
                async with self._reply_lock:
                    queue = self._reply_queues.get(correlation_id, None)
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
        
        func = self._function_table.get(function_name)
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



class RemoteControlNode:
    def __init__(self, mesh, name, *, timeout=None):
        self._mesh = mesh
        self._name = name
        self._timeout = timeout

        names = name.split('.', 1)
        if len(names) == 2:
            self._module_name = names[0]
            self._node_name = names[1]
        else:
            raise Exception(f'Mesh: bad remote node name: {self._name}')

            
    async def aio_set(self, value):
        reply = await self._mesh.aio_call_many(
            f'{self._module_name}._sd_node_call',
            [], { 'node_name': self._node_name, 'method': 'set', 'value': value },
            expected_replies=1, timeout=self._timeout
        )

        if len(reply) != 1:
            raise Exception(f'Mesh: remote node RPC error: {self._name}.aio_set(): no reply')
        if reply[0].get('status').lower() != 'ok':
            raise Exception(f'Mesh: remote node RPC error: {self._name}.aio_set(): {reply[0].get("message")}')

        return reply[0].get('return_value')

    
    async def aio_get(self):
        reply = await self._mesh.aio_call_many(
            f'{self._module_name}._sd_node_call',
            [], { 'node_name': self._node_name, 'method': 'get' },
            expected_replies=1, timeout=self._timeout
        )

        if len(reply) != 1:
            raise Exception(f'Mesh: remote node RPC error: {self._name}.aio_get(): no reply')
        if reply[0].get('status').lower() != 'ok':
            raise Exception(f'Mesh: remote node RPC error: {self._name}.aio_get(): {reply[0].get("message")}')

        return reply[0].get('return_value')



class Registry:
    def __init__(self, mesh, *, module_name='sd_mesh_registry'):
        self._mesh = mesh
        self._module_name = module_name

            
    async def aio_set(self, key, value, *, cas_revision:int|None=None) -> int|None:
        """
        Arguments:
          - key (str): key
          - value (Any): value to write
          - cas_revision (int|None): write only if the CAS revision matches; None not to use CAS
        Return Value (int|None): new CAS revision on success, None otherwise (typically CAS mismatch)
        """
        try:
            return await self._mesh.aio_call(f'{self._module_name}.set', key, value, cas_revision=cas_revision)
        except Exception as e:
            raise Exception(f'Registry.aio_set(): {e}')

    
    async def aio_get(self, key:str, default:Any=None, *, with_meta:bool=False) -> Any:
        """
        Arguments:
          - key (str): key for the element to read; if it ends with a separater character,
            the key is treated as a subtree prefix and the tree under it is returned as a dict.
          - default (Any): value to return if the key does not exist
          - with_meta (bool): if True, return the full registry record including the value and the meta info
        Return Value (Any): value or meta including the value on success, the provided default otherwise
        """
        try:
            return await self._mesh.aio_call(f'{self._module_name}.get', key, default, with_meta=with_meta)
        except Exception as e:
            raise Exception(f'Registry.aio_get(): {e}')
        

    async def aio_keys(self, prefix:str='', limit:int|None=1000)->list[str]:
        """
        Arguments:
          - prefix (str): key prefix for filtering
          - limit (int|None): maximum length of the list, None for no limit
        Return Value (list[str]): list of matching keys (full path including the prefix)
        """
        try:
            return await self._mesh.aio_call(f'{self._module_name}.keys', prefix, limit=limit)
        except Exception as e:
            raise Exception(f'Registry.aio_keys(): {e}')

    
    async def aio_delete(self, key:str, *, cas_revision:int|None=None) -> bool:
        """
        Arguments:
          - key (str): key for the element to delete
          - cas_revision (int|None): delete only if the CAS revision matches; None not to use CAS
        Return Value (bool): True on success, False otherwise (key error or CAS mismatch)
        """
        try:
            return await self._mesh.aio_call(f'{self._module_name}.delete', key, cas_revision=cas_revision)
        except Exception as e:
            raise Exception(f'Registry.aio_delete(): {e}')



class MeshPacket:
    def __init__(self):
        pass

    def pack(self):
        """
        - return value: tuple of (headers, body)
        """
        return (None, None)


    @classmethod
    def unpack(cls, headers, body):
        return MeshPacket()
    
