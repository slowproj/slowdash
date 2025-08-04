# Created by Sanshiro Enomoto on 24 May 2024 #

import sys, os, time, glob, asyncio, threading, inspect, logging

import slowlette
from sd_usermodule import UserModule
from sd_component import Component


class TaskFunctionThread(threading.Thread):
    def __init__(self, taskmodule, func, kwargs):
        super().__init__()
        self.taskmodule = taskmodule
        self.func = func
        self.kwargs = kwargs

        
    def run(self):
        if True:
            # avoid confusion by using the same loop in differen threads
            return self.run_in_own_eventloop()
        else:
            # some libraries require running in the same loop            
            return self.run_in_common_eventloop()    

        # TODO: implement a way to let users specify which loop to use (e.g., by @slowpy.mainloop)

    
    def run_in_common_eventloop(self):
        try:
            if inspect.iscoroutinefunction(self.func):
                future = asyncio.run_coroutine_threadsafe(
                    self.func(**self.kwargs),
                    self.taskmodule.user_thread.eventloop
                )
                future.result()
            else:
                self.func(**self.kwargs)
        except Exception as e:
            self.taskmodule.handle_error('task function error: %s' % str(e))


    def run_in_own_eventloop(self):
        self.eventloop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.eventloop)
        try:
            self.eventloop.run_until_complete(self.go())
        finally:
            # no "catch": propagate the error to make it visible for the user
            self.eventloop.close()
            self.eventloop = None

            
    async def go(self):
        try:
            if inspect.iscoroutinefunction(self.func):
                await self.func(**self.kwargs)
            else:
                self.func(**self.kwargs)
        except:
            self.taskmodule.handle_error('task function error: %s' % str(e))
            


        
class TaskModule(UserModule):
    def __init__(self, app, filepath, name, params, user_params):
        super().__init__(app, filepath, name, params, user_params)

        self.command_thread = None
        self.parallel_command_thread_set = set()
        self.namespace_prefix = params.get('namespace', {}).get('prefix', '%s.' % name.replace('-','_'))
        self.namespace_suffix = params.get('namespace', {}).get('suffix', '')

        logging.info(f'task module registered: {name}')
        
        
    def _preset_module(self, module):
        super()._preset_module(module)
        
        # inject SlowdashApp and obtain ControlSystem to/from task module
        def register(control_system):
            if self.app.control_system is None:
                self.app.control_system = control_system
                self.app.control_system._system_stop_event.clear()
        module.__dict__['_register'] = register
        module.__dict__['_slowdash_app'] = self.app        
        try:
            exec("from slowpy.control import ControlSystem", module.__dict__)
            exec("ControlSystem._slowdash_app = _slowdash_app", module.__dict__)
            exec("_register(ControlSystem())", module.__dict__)
        except Exception as e:
            self.handle_error('unable to import ControlSystem from task module: %s' % str(e))

            
    def _do_post_initialize(self):
        super()._do_post_initialize()
        
        # DEPRECIATED (July 2025)
        # _export() callback in slowtask script is depreciated, use ControlSystem.export(obj, name) instead
        # Putting prefix/suffix for the export names is for the old interface only.
        if True:
            func = self.get_func('_export')
            if func:
                try:
                    exports = func() or []
                except Exception as e:
                    self.handle_error('task module error: export(): %s' % str(e))
                    exports = []
                for name, node in exports:
                    export_name = '%s%s%s' % (self.namespace_prefix, name, self.namespace_suffix)
                    node.__slowdash_export_name = export_name
                    self.app.control_system._slowdash_exports.append((export_name, node))

                    value, datatype = node.get(), None
                    if type(value) is dict:
                        if 'table' in value:
                            datatype = 'table'
                        elif 'tree' in value:
                            datatype = 'tree'
                        elif 'bins' in value:
                            datatype = 'histogram'
                        elif 'ybins' in value:
                            datatype = 'histogram2d'
                        elif 'y' in value:
                            datatype = 'graph'
                        else:
                            datatype = 'json'
                    if datatype is not None:
                        channel =  {'name': export_name, 'type': datatype, 'current': True}
                    else:
                        channel =  {'name': export_name, 'current': True}
                    self.app.control_system._slowdash_channels[export_name] = channel
                    
        
            
    async def stop(self):
        self.touch_status()
        if self.user_thread and not self.user_thread.initialized_event.is_set():
            time.sleep(1)
            if not self.user_thread.initialized_event.is_set():
                logging.warning('User/Task module not yet initialized')
                
        if self.app.control_system is not None:
            logging.debug('calling ControlSystem.stop() in Task-Module "%s"' % self.name)
            self.app.control_system.stop()
            
        if self.command_thread is not None:
            if self.command_thread.is_alive():
                #kill
                pass
            self.command_thread.join(timeout=5)
            if self.command_thread.is_alive():
                logging.warning('timeout on terminating a task command thread')
            self.command_thread = None

        self.touch_status()
        for thread in self.parallel_command_thread_set:
            if thread.is_alive():
                #kill
                pass
            thread.join(timeout=5)
            if thread.is_alive():
                logging.warning('timeout on terminating a task thread')
        self.parallel_command_thread_set = set()
        self.touch_status()

        await super().stop()
        
        
    def match_namespace(self, name):
        if len(self.namespace_prefix) > 0:
            if not name.startswith(self.namespace_prefix):
                return ''
            else:
                name = name[len(self.namespace_prefix):]
        if len(self.namespace_suffix) > 0:
            if not name.endswith(self.namespace_suffix):
                return ''
            else:
                name = name[:-len(self.namespace_suffix)]
        if name.startswith('_'):
            return ''

        return name

            
    def is_command_running(self):
        return self.command_thread is not None and self.command_thread.is_alive()


    async def process_command(self, params):
        self.touch_status()
        result = await self.process_task_command(params)
        self.touch_status()
        if result is not None:
            if result is not True:
                logging.warning(f'Task Failed: {params}')
            return result
        
        return await super().process_command(params)
    

    async def process_task_command(self, doc):
        # parse the request
        function_name, params = '', {}
        is_await = False  # if True, wait for the command to complete before returning a response
        is_parallel = False  # if False, the command is rejected if another command is running
        for key, value in doc.items():
            if len(key) > 2 and key.endswith('()'):
                function_name = key[:-2]
                if function_name.startswith('parallel '):
                    is_parallel = True
                    function_name = function_name[8:].lstrip()
                if function_name.startswith('async '):  # backwards-compatibility
                    is_parallel = True
                    function_name = function_name[5:].lstrip()
                if function_name.startswith('await '):
                    is_await = True
                    function_name = function_name[5:].lstrip()
            else:
                params[key] = value

        # function
        function_name = self.match_namespace(function_name)
        if len(function_name) == 0:
            return None
        func = self.get_func(function_name)
        if func is None:
            return {'status': 'error', 'message': 'undefined function: %s' % function_name}

        # paramater binding by names, including types and defaults
        kwargs = {}
        var_keyword_param = None
        signature = inspect.signature(func)
        for name, attr in signature.parameters.items():
            if attr.kind == inspect.Parameter.VAR_KEYWORD:
                var_keyword_param = name
                continue
            if name in params:
                value = params[name]
            elif attr.default is not inspect._empty:
                value = attr.default
            else:
                logging.warn(f'Task: missing parameter: {name}')
                return {'status': 'error', 'message': f'missing parameter: {name}'}
            if attr.annotation in [ int, float, bool, str ]:
                try:
                    kwargs[name] = attr.annotation(value)
                except Exception as e:
                    logging.warn(f'Task: incompatible parameter value: {name}: {repr(value)}')
                    return {'status': 'error', 'message': f'incompatible parameter value: {name}: {repr(value)}'}
            else:
                kwargs[name] = value
        if var_keyword_param is not None:
            kwargs[var_keyword_param] = { k:v for k,v in params.items() if k not in kwargs }
        
        # task is single-threaded unless "parallel" is specified, except for loop()
        if not is_parallel and self.command_thread is not None:
            if self.command_thread.is_alive():
                return {'status': 'error', 'message': 'command already running'}
            else:
                self.command_thread.join()
        for thread in [ thread for thread in self.parallel_command_thread_set ]:
            if not thread.is_alive():
                thread.join()
                self.parallel_command_thread_set.remove(thread)

        # "await" waits for the command to complete before returning a response
        is_async = inspect.iscoroutinefunction(func)
        if is_await:
            try:
                if is_async:
                    await func(**kwargs)
                else:
                    func(**kwargs)
            except Exception as e:
                self.handle_error('task command error: %s' % str(e))
                return {'status': 'error', 'message': str(e) }
        else:
            this_thread = TaskFunctionThread(self, func, kwargs)
            this_thread.start()
            if is_parallel:
                self.parallel_command_thread_set.add(this_thread)
            else:
                self.command_thread = this_thread
        
        cmd = f"{self.name}.{function_name}({','.join(['%s=%s'%(key,repr(value)) for key,value in kwargs.items()])})"
        self.command_history.append((time.time(), cmd))
        logging.info(f'Task: {cmd}')
        
        return True



class SlowpyControl:
    def __init__(self, app):
        self.app = app
        
        self.exports = None
        self.channel_list = None
        
        
    async def get_channels(self):
        self.exports = {}
        self.channel_list = []
        
        if self.app.control_system is None:
            return []
        
        for name, node in self.app.control_system._slowdash_exports:
            self.exports[name] = node
                
        for name, channel in self.app.control_system._slowdash_channels.items():
            self.channel_list.append(channel)

        return self.channel_list

    
    async def get_data(self, channel):
        if self.exports is None:
            await self.get_channels()
        if channel not in self.exports:
            return None
        
        value = self.exports[channel].get()
        
        if type(value) in [ bool, int, float, str ]:
            return value
        elif type(value) == dict:
            if 'tree' in value or 'table' in value or 'bins' in value or 'ybin' in value or 'y' in value:
                return value
            else:
                return { 'tree': value }
        else:
            return str(value)

  

class TaskModuleComponent(Component):
    def __init__(self, app, project):
        super().__init__(app, project)

        self.taskmodule_list = []
        self.known_task_list = []
        self.status_revision = 1
        
        if not hasattr(app, 'control_system'):
            app.control_system = None
        self.slowpy_control = SlowpyControl(app)

        taskmodule_node = self.project.config.get('task', [])
        if not isinstance(taskmodule_node, list):
            taskmodule_node = [ taskmodule_node ]
                    
        task_table = {}
        for node in taskmodule_node:
            if not isinstance(node, dict):
                logging.error('bad slowtask configuration')
                continue
            if app.is_cgi and node.get('enabled_for_cgi', False) != True:
                continue
            if app.is_command and node.get('enabled_for_commandline', True) != True:
                continue
            if 'name' not in node:
                logging.error('name is required for slowtask module')
                continue

            name = node['name']
            filepath = node.get('file', './config/slowtask-%s.py' % name)
            task_table[name] = (filepath, node)
            self.known_task_list.append(name)
        
        # make a task entry list from the file list of the config dir
        if not app.is_cgi and self.project.project_dir is not None:
            for filepath in glob.glob(os.path.join(self.project.project_dir, 'config', 'slowtask-*.py')):
                rootname, ext = os.path.splitext(os.path.basename(filepath))
                kind, name = rootname.split('-', 1)
                if name not in self.known_task_list:
                    task_table[name] = (filepath, {})
                    self.known_task_list.append(name)

        for name, (filepath, params) in task_table.items():
            user_params = params.get('parameters', {})
            module = TaskModule(app, filepath, name, params, user_params)
            if module is None:
                logging.error('Unable to load slowtask module: %s' % filepath)
            else:
                module.auto_load = params.get('auto_load', False)
                self.taskmodule_list.append(module)

                
    @slowlette.on_event('startup')
    async def startup(self):
        await asyncio.gather(*(module.start() for module in self.taskmodule_list if module.auto_load))


    @slowlette.on_event('shutdown')
    async def shutdown(self):
        await asyncio.gather(*(module.stop() for module in self.taskmodule_list))
            
        if len(self.taskmodule_list) > 0:
            logging.info('slowtask modules terminated')

        self.taskmodule_list = []
        

    def public_config(self):
        if len(self.taskmodule_list) == 0:
            return None
        
        return {
            'task_module': {
                module.name: { 'auto_load': module.auto_load } for module in self.taskmodule_list
            }
        }


    @slowlette.get('/api/channels')
    async def api_channels(self):
        return await self.slowpy_control.get_channels()

    
    @slowlette.get('/api/data/{channels}')
    async def api_data(self, channels:str, opts:dict):
        try:
            channels = channels.split(',')
            length = float(opts.get('length', 3600))
            to = float(opts.get('to', 0))
        except Exception as e:
            logging.error('Bad data URL: %s: %s' % (str(opts), str(e)))
            return False

        now = time.time()
        if (to < 0) or (to > 0 and (now > to+1 or now < to - length)):
            return {}
        start = to if to > 0 else now + to

        result = {}
        for ch in channels:
            data = await self.slowpy_control.get_data(ch)
            if data is not None:
                result[ch] = {
                    'start': start, 'length': length,
                    't': now - start,
                    'x': data
                }

        return result


    @slowlette.post('/api/update/tasklist')
    async def update_tasklist(self):
        if self.app.is_cgi or (self.project.project_dir is None):
            return slowlette.Response(200)
        
        for filepath in glob.glob(os.path.join(self.project.project_dir, 'config', 'slowtask-*.py')):
            rootname, ext = os.path.splitext(os.path.basename(filepath))
            kind, name = rootname.split('-', 1)
            if name in self.known_task_list:
                continue
            self.known_task_list.append(name)

            module = TaskModule(filepath, name, {})
            if module is None:
                logging.error('Unable to load control module: %s' % filepath)
            else:
                module.auto_load = False
                self.taskmodule_list.append(module)

        return {'status': 'ok'}

    
    @slowlette.get('/api/control/task')
    async def task_status(self, since:int=0):
        while self.app.is_async and self.status_revision <= since:
            has_update = False
            for module in self.taskmodule_list:
                if module.was_running != module.is_running():
                    module.touch_status()
                if module.status_revision > self.status_revision:
                    self.status_revision = module.status_revision
                    has_update = True
            if not has_update:
                await asyncio.sleep(0.2)
            
        result = {
            'revision': self.status_revision,
            'tasks': []
        }
        for module in self.taskmodule_list:
            last_routine = module.routine_history[-1] if len(module.routine_history) > 0 else None
            last_command = module.command_history[-1] if len(module.command_history) > 0 else None
            doc = {
                'name': module.name,
                'is_loaded': module.is_loaded(),
                'is_routine_running': module.is_running(),
                'is_command_running': module.is_command_running(),
                'is_waiting_input': module.is_waiting_input(),
                'is_stopped': module.is_stopped(),
                'last_routine_time': last_routine[0] if last_routine is not None else None,
                'last_routine': last_routine[1] if last_routine is not None else None,
                'last_command_time': last_command[0] if last_command is not None else None,
                'last_command': last_command[1] if last_command is not None else None,
                'last_log': '',
                'has_error': module.error is not None,
            }
            result['tasks'].append(doc)

        return result

        
    @slowlette.post('/api/control')
    async def execute_command(self, doc:slowlette.DictJSON):
        if len(self.taskmodule_list) == 0:
            return None
        
        # unlike GET, only one module can process to POST
        for module in self.taskmodule_list:
            result = await module.process_command(dict(doc))
            if result is not None:
                break
        else:
            return None

        if type(result) is bool:
            if result:
                return {'status': 'ok'}
            else:
                return {'status': 'error'}
        elif type(result) is int:
            return slowlette.Response(result)
                
        return result

    
    @slowlette.post('/api/control/task/{taskname}')
    async def control_task(self, taskname:str, doc:slowlette.DictJSON):
        action = doc.get('action', None)
        logging.info(f'Task Control: {taskname}.{action}()')
        
        for module in self.taskmodule_list:
            if module.name != taskname:
                continue
            if action == 'start':
                await module.start()
                return {'status': 'ok'}
            elif action == 'stop':
                await module.stop()
                return {'status': 'ok'}
            else:
                return { 'status': 'error', 'message': f'unknown command: {action}' }
            
        return { 'status': 'error', 'message': f'unknown task: {taskname}' }
