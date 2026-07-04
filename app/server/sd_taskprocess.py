# Created by Sanshiro Enomoto on 3 June 2026 #

import sys, os, time, re, json, asyncio, copy, logging
from typing import Any
from pathlib import Path

import slowlette
from sd_component import Component
from slowpy.mesh import Mesh


class MeshRequest:
    def __init__(self, doc:dict):
        self.topic_name:str|None = None
        self.module_name:str = ''
        self.function_name:str = ''
        self.params:dict = {}
        self.error:str|None = None

        self._parse(doc)


    def __str__(self):
        if self.error is not None:
            return f'Error({self.error})'

        if self.topic_name is not None:
            name = f'publish {self.topic_name}'
        elif self.module_name:
            name = self.module_name + '.' + (self.function_name or '[NO_FUNCTION_NAME]')
        else:
            name = '[INVALID_NAME]'
        
        return name + f'({",".join([k+"="+repr(v) for k,v in self.params.items()])})'

    
    def _parse(self, doc:dict):
        topic_name, module_name, function_name, params = None, '', '', {}

        name, args = '', ''
        for key, value in doc.items():
            if len(key) > 2 and ('(' in key) and key.endswith(')'):
                [name, args] = key.split('(', 1)
                if name.lower().startswith('publish '):
                    topic_name = name[len('publish '):]
                else:
                    split_names = name.split('.', 1)
                    if len(split_names) == 2:
                        [module_name, function_name] = split_names
            else:
                params[key] = value
                
        if topic_name is not None:
            if not topic_name[0].isalpha() or not topic_name.replace('_','a').replace('.','a').replace('/','a').isalnum():
                self.error = f'bad topic name: {name}'
                return
        elif len(module_name) == 0 or not module_name[0].isalpha() or not module_name.replace('_', 'a').isalnum():
            self.error = f'bad module name: {name}'
            return
        elif len(function_name) == 0 or not function_name[0].isalpha() or not function_name.replace('_', 'a').isalnum():
            self.error = f'bad function name: {name}'
            return

        arg_params = {}
        key, value = '', ''
        in_key, quote = True, None
        for ch in args:
            if in_key:
                if ch == ' ':
                    pass
                elif ch == '=':
                    in_key = False
                elif ch == ')':
                    if (len(key) > 0):
                        self.error = f'{name}: bad argument list: {args}'
                        return
                    break
                else:
                    if (len(key) == 0 and not ch.isalpha()) or (not ch.isalnum()):
                        self.error = f'{name}: bad argument name: {args}'
                        return
                    key += ch
            else:
                if ch in [ '"', "'" ]:
                    if ch == quote:
                        quote = None
                    else:
                        quote = ch
                if ch not in  [',', ')'] or quote is not None:
                    value += ch
                else:
                    arg_params[key] = value
                    key, value = '', ''
                    in_key = True
        if len(key) > 0 or len(value) > 0:
            self.error = f'{name}: bad argument list: {args}'
            return
        
        params.update(arg_params)
        for key, value in params.items():
            if not key.replace('_', 'a').isalnum():
                self.error = f'{name}: bad parameter name: {key}'
                self.params = {}
                return
            try:
                self.params[key] = json.loads(value)
            except Exception:
                self.params[key] = value

        if topic_name is not None:
            self.topic_name = topic_name
        else:
            self.module_name = module_name
            self.function_name = function_name
                

            
class TaskFunctionProxy:
    class Argument:
        def __init__(self, arg_name:str, arg_spec:dict):
            self.name = arg_name
            
            value_type = arg_spec.get('type')
            if value_type == 'int':
                self.Type = int
            elif value_type == 'float':
                self.Type = float
            elif value_type == 'str':
                self.Type = str
            elif value_type == 'bool':
                self.Type = bool
            else:
                self.Type = None

            self.has_default = ('default' in arg_spec)
            self.default_value = arg_spec.get('defalut')

            
        def apply(self, params:dict[str,Any]):
            if self.name not in params:
                if self.has_default:
                    return self.default_value
                else:
                    raise Exception(f'keyword argument required: {self.name}')

            value = params.get(self.name)
            if self.Type is None:
                return value
            
            try:
                return self.Type(value)
            except:
                raise Exception(f'"{self.name}": expected a {self.Type.__name__}, received: {value}')
                

    def __init__(self, name:str, func_spec:dict):
        self.name = name
        self.has_arbitrary_keywords = func_spec.get('arbitrary_keywords', False)
        self.kwargs = {
            arg_name: self.Argument(arg_name, arg_spec)
            for arg_name, arg_spec in func_spec.get('kwargs', {}).items()
        }


    def match_kwargs(self, params:dict[str,Any]):
        kwargs = {}
        for arg_name, arg in self.kwargs.items():
            kwargs[arg_name] = arg.apply(params)
            
        if self.has_arbitrary_keywords:
            for param_name, param_value in params.items():
                if param_name not in kwargs:
                    kwargs[param_name] = param_value

        return kwargs
            


class TaskVariableProxy:
    def __init__(self, name:str, var_spec:dict):
        self.name = name
        self.spec = copy.deepcopy(var_spec)
        
        self._remote_node = None


    async def aio_get(self, mesh:Mesh):
        if not self._remote_node:
            self._remote_node = mesh.remote_node(self.name)

        return await self._remote_node.aio_get()
            
            
    
class TaskProxy:
    def __init__(self, taskspec:dict):
        self._spec = copy.deepcopy(taskspec)
        
        self._mesh_id = self._spec['mesh_id']
        self._name = self._spec.get('name', self._mesh_id)
        self._heartbeat_expire = self._spec.get('timestamp', time.time()) + self._spec.get('heartbeat_interval', 0)
        
        self._functions = {
            func_name: TaskFunctionProxy(func_name, func_spec)
            for func_name, func_spec in self._spec.get('functions', {}).items()
        }
        self._variables = {
            var_name: TaskVariableProxy(f'{self._name}.{var_name}', var_spec)
            for var_name, var_spec in self._spec.get('variables', {}).items()
        }
        self._contents = {
            cont_name: { 'content_type': cont_spec.get('content_type') }
            for cont_name, cont_spec in self._spec.get('contents', {}).items()
        }

        
    @property
    def name(self):
        return self._name

    
    @property
    def spec(self):
        return self._spec


    @property
    def contents(self):
        return self._contents


    async def process_command(self, request:MeshRequest, mesh:Mesh):
        if request.module_name != self._name:
            return None
        
        function = self._functions.get(request.function_name, None)
        if function is None:
            logging.warning(f'Task Command: no such function: {request}')
            return {'status': 'error', 'message': f'no such function: {request}' }
        try:
            kwargs = function.match_kwargs(request.params)
        except Exception as e:
            logging.warning(f'Task Command: function parameter mismatch: {request}: {e}')
            return {'status': 'error', 'message': f'function parameter mismatch: {e}' }
            
        logging.info(f'Dispatch Task RPC: {request} --> {self._mesh_id}')
        try:
            reply = await mesh.aio_call_many(
                f'{request.module_name}.{request.function_name}',
                args=[], kwargs=kwargs,
                expected_replies=1, timeout=5, raise_on_timeout=True
            )
        except Exception as e:
            logging.warning(f'Task Command: RPC error: {request}: {e}')
            return {'status': 'error', 'message': f'RPC error: {e}' }

        if len(reply) < 1:
            logging.warning(f'Task Command: RPC error: {request}: no reply')
            return {'status': 'error', 'message': f'RPC error: no reply' }

        return reply[0]

    
    async def get_channels(self):
        channels = []
        for var in self._variables.values():
            data_type = var.spec.get('data_type')
            if data_type is not None:
                channels.append({ 'name': var.name, 'type': data_type })
            else:
                channels.append({ 'name': var.name })
                                
        return channels

    
    async def get_data(self, name:str, mesh:Mesh):
        if not name.startswith(self._name + '.'):
            return None

        var_name = name[len(self._name)+1:]
        variable = self._variables.get(var_name, None)
        if variable is None:
            return None

        logging.debug(f'Dispatch Variable Get: {name} --> {self._mesh_id}')
        try:
            value = await variable.aio_get(mesh)
        except Exception as e:
            return { 'status': 'error', 'message': f'Remote Variable Read Error: {name}: {e}'}

        return { 'status': 'ok', 'return_value': value }

    
    async def get_content(self, name:str, mesh:Mesh):
        if name not in self._contents:
            return None

        try:
            reply = await mesh.aio_call_many(
                f'{self._name}._sd_get_content',
                args=[name], kwargs={},
                expected_replies=1, timeout=5, raise_on_timeout=True
            )
        except Exception as e:
            logging.warning(f'Task Content: RPC error: {self._name}._sd_get_content("{name}"): {e}')
            return None

        if len(reply) < 1:
            logging.warning(f'Task Content: RPC error: {self._name}._sd_get_content("{name}"): no reply')
            return None

        if reply[0].get('status').lower() != 'ok':
            logging.warning(f'Task Content: {self._name}._sd_get_content("{name}"): {reply[0].get("message")}')

        content_type = self._contents[name].get('content_type')
        content = reply[0].get('return_value')
        
        return content_type, content
        
        
    

class TaskProcessComponent(Component):
    def __init__(self, app, project):
        super().__init__(app, project)

        self._mesh = None
        self._task_table: dict[str, TaskProcess] = {}   # { mesh_id: task }

        self._content_table: dict[str,str] = {}   # { content_name: file_name }


    @slowlette.on_event('post_startup')
    async def startup(self):
        # this needs to be done in "post_startup", as SlowMQ (if used) must be running.
        if self._mesh is None:
            self._mesh = Mesh('slowmq://localhost:18881', name="sd_taskprocess")        
            await self._subscribe_taskspec()
            await self._mesh.aio_start()
            await self._request_taskspec()

        
    @slowlette.on_event('shutdown')
    async def shutdown(self):
        if self._mesh is not None:
            await self._mesh.aio_stop()


    async def _subscribe_taskspec(self):
        async def process_task_spec(headers, data):
            mesh_id = data.get('mesh_id')
            if mesh_id is not None and len(mesh_id) > 0:
                self._task_table[mesh_id] = TaskProxy(data)
                logging.info(f'Task spec received: {data}')
                
        await self._mesh.aio_subscribe('sd.task.spec.>', process_task_spec)
        
        async def process_task_exit(headers, data):
            mesh_id = data.get('mesh_id')
            if mesh_id is not None and len(mesh_id) > 0:
                if mesh_id in self._task_table:
                    self._task_table.pop(mesh_id, None)
                    logging.info(f'Task removed: {mesh_id}')
                
        await self._mesh.aio_subscribe('sd.task.exit.>', process_task_exit)
        
        async def process_task_heartbeat(headers, data):
            mesh_id = headers.get('mesh_id')
            if mesh_id is not None and len(mesh_id) > 0:
                if mesh_id not in self._task_table:
                    logging.warning(f'Heartbeat from an unknown task: {mesh_id}')
                    await self._mesh.aio_publish('sd.task.control.introduce', {})
                else:
                    self._task_table[mesh_id]._heartbeat_expire = data.get('expire', 0)
            
        await self._mesh.aio_subscribe('sd.task.heartbeat.>', process_task_heartbeat)
        
        
    async def _request_taskspec(self):
        await self._mesh.aio_publish('sd.task.control.introduce', {})

        
    async def _check_task_heartbeats(self):
        now = time.time() - 5
        dead_tasks = []
        for mesh_id, task in self._task_table.items():
            if task._heartbeat_expire < now:
                dead_tasks.append(mesh_id)
                logging.warning(f'No Heartbeat from Task: {task.name}')
        for mesh_id in dead_tasks:
            self._task_table.pop(mesh_id, None)

            
    @slowlette.get('/api/task/specs')
    async def get_tasklist(self):
        doc = []
        await self._check_task_heartbeats()
        for task in list(self._task_table.values()):
            doc.append(task.spec)
        return doc

    
    @slowlette.post('/api/control')
    async def execute_command(self, doc:slowlette.DictJSON):
        logging.info(f'Task Command: {doc}')
        # unlike GET, only one module can process a POST request

        request = MeshRequest(dict(doc))
        if request.error is not None:
            return {'status': 'error', 'message': request.error }

        if request.topic_name is not None:
            try:
                await self._mesh.aio_publish(request.topic_name, request.params)
                return {'status': 'ok'}
            except Exception as e:
                return {'status': 'error', 'message': str(e) }
            
        await self._check_task_heartbeats()
        for task in list(self._task_table.values()):
            result = await task.process_command(request, self._mesh)
            if result is not None:
                break
        else:
            return None

        return result


    @slowlette.get('/api/channels')
    async def api_channels(self):
        channels = []
        await self._check_task_heartbeats()
        for task in list(self._task_table.values()):
            channels.extend(await task.get_channels())

        return channels

    
    class DataMergerResponse(slowlette.Response):
        def __init__(self, record):
            super().__init__(content=None)
            self.record = record

            
        def merge_response(self, response) -> None:
            """append the "current" data from this task to the response (typiaclly data from storage)
               - only if the channel does not exist, or
               - the last data point is older than the "current" data (it always should be, though)
            """
            if response.content is None:
                response.content = {}
            elif type(response.content) is not dict:
                self.content = self.record
                super().merge_response(response)
                return

            for ch in self.record:
                if ch not in response.content:
                    response.content[ch] = self.record[ch]
                    continue

                data, my_data = response.content[ch], self.record[ch]
                t0, my_t0 = data.get('start', 0), my_data['start']
                t, my_t = data.get('t', None), my_data['t']
                if type(t) is list:
                    if len(t) == 0 or t0 + t[-1] < my_t0 + my_t:
                        data['t'].append(my_t + my_t0 - t0)
                        data['x'].append(my_data['x'])
                elif t is not None:
                    if t0 + t < my_t0 + my_t:
                        data['t'] = [ t, my_t + my_t0 - t0 ]
                        data['x'] = [ data.get('x', None), my_data['x'] ]
                else:
                    data['start'] = my_t0
                    data['t'] = my_t
                    data['x'] = my_data['x']

            self.content = None
            if len(response.content) > 0:
                response.status_code = 200
                
            super().merge_response(response)

            
    @slowlette.get('/api/data/{*}')
    async def api_get_data(self, request:slowlette.Request, length:float=3600, to:float=0):
        channels = request.path_str[len('/api/data/'):]   # channel name might contain "/"
        
        now = time.time()
        if (to < 0) or (to > 0 and (now > to+1 or now < to - length)):
            return {}
        
        await self._check_task_heartbeats()
        
        record = {}
        start = (to if to > 0 else int(now) + to) - length
        for ch in channels.split(',') if channels else []:
            for task in list(self._task_table.values()):
                reply = await task.get_data(ch, self._mesh)
                if reply is None:
                    continue
                if reply.get('status') != 'ok':
                    logging.warning(f'Task: {reply.get('message')}')
                    continue
                
                record[ch] = {
                    'start': start, 'length': length,
                    't': now - start,
                    'x': reply.get('return_value')
                }

        return self.DataMergerResponse(record)
    

    @slowlette.get('/api/config/contentlist')
    async def api_get_content_list(self):
        self._content_table = {}

        await self._check_task_heartbeats()
        
        doc = []
        for task in list(self._task_table.values()):
            for content_file_name in task.contents:
                if not content_file_name.startswith('config/'):
                    continue
                config_file = content_file_name[len('config/'):]
                root_name = Path(config_file).stem
                kind, name = root_name.split('-', 1)
                if kind not in [ 'slowdash', 'slowplot', 'slowcruise', 'html' ]:
                    continue
                
                doc.append({
                    'type': kind,
                    'name': name,
                    'mtime': int(time.time()),
                    'title': '',
                    'description': '',
                    'config_file': config_file,
                    'config_error': '',
                    'config_error_line': '',
                })
                self._content_table[f'{kind}-{name}'] = content_file_name
                        
        return doc

    
    @slowlette.get('/api/config/content/{content_name}')
    async def api_get_content(self, content_name:str):
        content_file_name = self._content_table.get(content_name)
        if content_file_name is None:
            return None
        
        await self._check_task_heartbeats()
        for task in list(self._task_table.values()):
            result = await task.get_content(content_file_name, self._mesh)
            if result is not None:
                break
        else:
            return None

        content_type, content = result
        return slowlette.Response(200, content_type=content_type, content=content)

