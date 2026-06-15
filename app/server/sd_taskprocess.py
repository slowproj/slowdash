# Created by Sanshiro Enomoto on 3 July 2026 #

import sys, os, time, re, json, asyncio, copy, logging

import slowlette
from sd_component import Component
from slowpy.mesh import Mesh


class FunctionCallRequest:
    def __init__(self, doc:dict):
        self.module_name = ''
        self.function_name = ''
        self.params = {}
        self.error = None

        self._parse(doc)


    def __str__(self):
        if self.error is not None:
            return f'Error({self.error})'
        
        return (''
            + f'{self.module_name or "[NO_MODULE_NAME]"}.{self.function_name or "[NO_FUNCTION_NAME]"}'
            + f'({",".join([k+"="+repr(v) for k,v in self.params.items()])})'
        )
                
    def _parse(self, doc:dict):
        module_name, function_name, params, error = '', '', {}, None
        
        name, args = '', ''
        for key, value in doc.items():
            if len(key) > 2 and ('(' in key) and key.endswith(')'):
                [name, args] = key.split('(', 1)
                [module_name, function_name] = name.split('.', 1)
            else:
                params[key] = value

        if len(module_name) == 0 or not module_name[0].isalpha() or not module_name.replace('_', 'a').isalnum():
            error = f'bad module name: {name}'
            args = ''
        elif len(function_name) == 0 or not function_name[0].isalpha() or not function_name.replace('_', 'a').isalnum():
            error = f'bad function name: {name}'
            args = ''

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
                        error = f'{name}: bad argument list: {args}'
                    break
                else:
                    if (len(key) == 0 and not ch.isalpha()) or (not ch.isalnum()):
                        error = f'{name}: bad argument name: {args}'
                        break
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
            error = f'{name}: bad argument list: {args}'

        if error is not None:
            self.error = re.sub(r'[^A-Za-z0-9_.,:;()= ]', '?', error)  # sanitize log message
        else:
            self.module_name = module_name
            self.function_name = function_name
            params.update(arg_params)
            for key, value in params.items():
                try:
                    self.params[key] = json.loads(value)
                except Exception:
                    self.params[key] = value

                

class Task:
    def __init__(self, taskspec:dict):
        self._spec = copy.deepcopy(taskspec)
        
        self._mesh_id = self._spec['mesh_id']
        self._name = self._spec.get('name', self._mesh_id)
        self._functions = set([ f['name'] for f in self._spec.get('functions', []) ])
        self._variables = set([ v['name'] for v in self._spec.get('variables', []) ])

    @property
    def name(self):
        return self._name

    @property
    def spec(self):
        return self._spec


    async def process_command(self, request: FunctionCallRequest, mesh:Mesh) -> bool|str|None:
        if request.module_name != self._name:
            return None
        if request.function_name not in self._functions:
            return f'no such function: {request}'
                
        # TODO: match the arguments

        logging.info(f'Dispatch Task RPC: {request} --> {self._mesh_id}')
        try:
            return_value = await mesh.aio_call_many(
                f'{request.module_name}.{request.function_name}',
                args=[], kwargs=request.params,
                multiple_replies=False, timeout=5, raise_on_timeout=True
            )
        except Exception as e:
            logging.error(f'RPC ERROR: {e}')
            return str(e)

        if isinstance(return_value, dict) and return_value.get('status', 'ok').lower() != 'ok':
            return return_value
        
        return True
        
            


class TaskProcessComponent(Component):
    def __init__(self, app, project):
        super().__init__(app, project)

        self._mesh = None
        self._task_table: dict[str, TaskProcess] = {}   # { mesh_id: task }


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
                self._task_table[mesh_id] = Task(data)
            logging.info(f'Task spec received: {data}')
            
        await self._mesh.aio_subscribe('sd.task.spec.>', process_task_spec)
        
        
    async def _request_taskspec(self):
        await self._mesh.aio_publish('sd.task.control.introduce', {})

        
    @slowlette.get('/api/task')
    async def get_tasklist(self):
        doc = []
        for task in self._task_table.values():
            doc.append(task.spec)
        return doc

    
    @slowlette.post('/api/control')
    async def execute_command(self, doc:slowlette.DictJSON):
        logging.info(f'Task Command: {doc}')
        if not self._task_table:
            return None

        # unlike GET, only one module can process a POST request

        request = FunctionCallRequest(dict(doc))
        if request.error is not None:
            return {'status': 'error', 'message': request.error }
        
        for task in self._task_table.values():
            result = await task.process_command(request, self._mesh)
            if result is not None:
                break
        else:
            return None

        if isinstance(result, bool):
            if result:
                return {'status': 'ok'}
            else:
                return {'status': 'error'}
        elif isinstance(result, str):
            return {'status': 'error', 'message': result}
                
        return result
