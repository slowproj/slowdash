# Created by Sanshiro Enomoto on 24 May 2024 #

import sys, os, time, glob, json, threading, logging

from slowapi import SlowAPI, Response
from sd_usermodule import UserModule
from sd_component import Component


class TaskFunctionThread(threading.Thread):
    def __init__(self, taskmodule, func, kwargs):
        super().__init__()
        self.taskmodule = taskmodule
        self.func = func
        self.kwargs = kwargs

    def run(self):
        try:
            self.func(**self.kwargs)
        except Exception as e:
            self.taskmodule.handle_error('task function error: %s' % str(e))


        
class TaskModule(UserModule):
    def __init__(self, filepath, name, params):
        super().__init__(filepath, name, params)
        
        self.command_thread = None
        self.async_command_thread_set = set()
        self.exports = None
        self.channel_list = None
        self.namespace_prefix = params.get('namespace_prefix', '%s.' % name)
        self.namespace_suffix = params.get('namespace_suffix', '')

        self.control_system = None
        
        logging.info('task module registered')
        
        
    def _preset_module(self, module):
        super()._preset_module(module)

        # obtain a reference to the ControlSystem class in the task module
        def register(control_system):
            self.control_system = control_system
            self.control_system._global_stop_event.clear()

        module.__dict__['_register'] = register
        try:
            exec("from slowpy.control import ControlSystem", module.__dict__)
            exec("_register(ControlSystem())", module.__dict__)
        except Exception as e:
            self.handle_error('unable to load task module: %s' % str(e))

        
    def load(self):
        self.exports = None
        self.channel_list = None
        
        return super().load()

            
    def stop(self):
        if self.user_thread and not self.user_thread.initialized_event.is_set():
            time.sleep(1)
            if not self.user_thread.initialized_event.is_set():
                logging.warining('User/Task module not yet initialized')
                
        if self.control_system is not None:
            logging.debug('calling ControlSystem.stop() in Task-Module "%s"' % self.name)
            self.control_system.stop()
            
        if self.command_thread is not None:
            if self.command_thread.is_alive():
                #kill
                pass
            self.command_thread.join()
            self.command_thread = None

        for thread in self.async_command_thread_set:
            if thread.is_alive():
                #kill
                pass
            thread.join()
        self.async_command_thread_set = set()

        super().stop()
        
        
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

            
    def get_variable(self, name):
        if name not in self.exports:
            self.scan_channels()
            if name not in self.exports:
                return None

        return self.exports[name]

        
    def is_command_running(self):
        return self.command_thread is not None and self.command_thread.is_alive()


    def scan_channels(self):
        self.channel_list = []
        self.exports = {}
        
        func = self.get_func('_export')
        if func is None:
            return
        
        try:
            exports = func()
        except Exception as e:
            self.handle_error('task module error: export(): %s' % str(e))
            return None
        if exports is None:
            return

        for name, node in exports:
            external_name = '%s%s%s' % (self.namespace_prefix, name, self.namespace_suffix)
            self.exports[external_name] = node
            value = node.get()
            if type(value) == dict:
                if 'table' in value:
                    self.channel_list.append({'name': external_name, 'type': 'table'})
                elif 'tree' in value:
                    self.channel_list.append({'name': external_name, 'type': 'tree'})
                elif 'bins' in value:
                    self.channel_list.append({'name': external_name, 'type': 'histogram'})
                elif 'ybins' in value:
                    self.channel_list.append({'name': external_name, 'type': 'histogram2d'})
                elif 'y' in value:
                    self.channel_list.append({'name': external_name, 'type': 'graph'})
                else:
                    self.channel_list.append({'name': external_name, 'type': 'tree'})
            else:
                self.channel_list.append({'name': external_name})

        return self.channel_list
    
                
    def get_channels(self):
        return self.scan_channels()

    
    def get_data(self, channel):
        if self.channel_list is None:
            self.scan_channels()
            
        if channel not in self.exports:
            self.scan_channels()
            if channel not in self.exports:
                return None

        value = self.get_variable(channel).get()
        
        if type(value) in [ bool, int, float, str ]:
            return value
        elif type(value) == dict:
            if 'tree' in value or 'table' in value or 'bins' in value or 'ybin' in value or 'y' in value:
                return value
            else:
                return { 'tree': value }
        else:
            return str(value)

    
    def process_command(self, params):
        result = self.process_task_command(params)
        if result is not None:
            return result
        
        if self.module is None or self.func_process_command is None:
            return None
        
        try:
            result = self.func_process_command(params)
        except Exception as e:
            self.handle_error('task module error: process_command(): %s' % str(e))
            return {'status': 'error', 'message': str(e) }

        if result is not None:
            self.command_history.append((
                time.time(),
                '_process_command(%s)' % ','.join(['%s=%s' % (k,v) for k,v in params.items()])
            ))
        
        return result
    

    def process_task_command(self, params):
        variable_name, function_name, kwargs = '', '', {}
        is_await = False  # if True, wait for the command to complete before returning a response
        is_async = False  # if False, the command is rejected if another command is running
        for key, value in params.items():
            if len(key) > 2 and key.endswith('()'):
                function_name = key[:-2]
                if function_name.startswith('await '):
                    is_await = True
                    function_name = function_name[5:].lstrip()
                if function_name.startswith('async '):
                    is_async = True
                    function_name = function_name[5:].lstrip()
            elif len(key) > 1 and key.startswith('@'):
                variable_name = key[1:]
            else:
                kwargs[key] = value

        # direct writing to mapped variables
        variable_name = self.match_namespace(variable_name)
        if len(variable_name) > 0:
            var = self.get_variable(variable_name)
            if var is None:
                return {'status': 'error', 'message': 'undefined control variable: "%s"' % variable_name }
            try:
                var.set(value)
            except Exception as e:
                return {'status': 'error', 'message': str(e) }
            return True

        # function call
        function_name = self.match_namespace(function_name)
        if len(function_name) == 0:
            return None
        func = self.get_func(function_name)
        if func is None:
            return {'status': 'error', 'message': 'undefined function: %s' % function_name}

        # task is single-threaded unless "async" is specified, except for loop()
        if not is_async and self.command_thread is not None:
            if self.command_thread.is_alive():
                return {'status': 'error', 'message': 'command already running'}
            else:
                self.command_thread.join()
        for thread in [ thread for thread in self.async_command_thread_set ]:
            if not thread.is_alive():
                thread.join()
                self.async_command_thread_set.remove(thread)
        
        cmd = '%s.%s(%s)' % (self.name, function_name, ','.join(['%s=%s'%(key,value) for key,value in kwargs.items()]))
        self.command_history.append((time.time(), cmd))
        
        # "await" waits for the command to complete before returning a response
        if is_await:
            try:
                func(**kwargs)
            except Exception as e:
                self.handle_error('task command error: %s' % str(e))
                return {'status': 'error', 'message': str(e) }
        else:
            this_thread = TaskFunctionThread(self, func, kwargs)
            this_thread.start()
            if is_async:
                self.async_command_thread_set.add(this_thread)
            else:
                self.command_thread = this_thread
            
        return True



class TaskModuleComponent(Component):
    def __init__(self, app, project):
        super().__init__(app, project)

        self.taskmodule_list = []
        self.known_task_list = []

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
            params = node.get('parameters', {})
            task_table[name] = (filepath, params, {'auto_load':node.get('auto_load', False)})
            self.known_task_list.append(name)
        
        # make a task entry list from the file list of the config dir
        if not app.is_cgi and self.project.project_dir is not None:
            for filepath in glob.glob(os.path.join(self.project.project_dir, 'config', 'slowtask-*.py')):
                rootname, ext = os.path.splitext(os.path.basename(filepath))
                kind, name = rootname.split('-', 1)
                if name not in self.known_task_list:
                    task_table[name] = (filepath, {}, {'auto_load':False})
                    self.known_task_list.append(name)

        for name, (filepath, params, opts) in task_table.items():
            module = TaskModule(filepath, name, params)
            if module is None:
                logging.error('Unable to load slowtask module: %s' % filepath)
            else:
                module.auto_load = opts.get('auto_load', False)
                self.taskmodule_list.append(module)
                
        for module in self.taskmodule_list:
            if module.auto_load:
                module.start()

                
    def terminate(self):
        for module in self.taskmodule_list:
            module.stop()
            
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


    @SlowAPI.get('/channels')
    def api_channels(self):
        result = []
        for taskmodule in self.taskmodule_list:
            channels = taskmodule.get_channels()
            if channels is not None:
                result.extend(channels)
        return result

        
    @SlowAPI.get('/data/{channels}')
    def api_data(self, channels:str, opts:dict):
        try:
            channels = channels.split(',')
            length = float(opts.get('length', '3600'))
            to = float(opts.get('to', int(time.time())+1))
        except Exception as e:
            logging.error('Bad data URL: %s: %s' % (str(opts), str(e)))
            return Response(400)
        
        has_result, result = False, {}
        start = to - length
        t = time.time() - start
        if t >= 0 and t <= length + 10:
            for taskmodule in self.taskmodule_list:
                for ch in channels:
                    data = taskmodule.get_data(ch)
                    if data is None:
                        continue
                    has_result = True
                    result[ch] = {
                        'start': start, 'length': length,
                        't': t,
                        'x': data
                    }

        return result if has_result else None


    @SlowAPI.post('/update/tasklist')
    def update_tasklist(self):
        if self.app.is_cgi or (self.project.project_dir is None):
            return Response(200)
        
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

    
    @SlowAPI.get('/control/task')
    def task_status(self):
        result = []
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
                'has_error': module.error is not None
            }
            result.append(doc)

        return result

        
    @SlowAPI.post('/control')
    def execute_command(self, body:bytes):
        try:
            doc = json.loads(body.decode())
        except Exception as e:
            logging.error('control: JSON decoding error: %s' % str(e))
            return Response(400) # Bad Request
            
        result = None
        logging.info(f'Task Command: {doc}')
        
        # unlike GET, only one module can process to POST
        for module in self.taskmodule_list:
            result = module.process_command(doc)
            if result is not None:
                break
        
        if type(result) is bool:
            if result:
                return {'status': 'ok'}
            else:
                return {'status': 'error'}
        elif type(result) is int:
            return Response(result)
                
        return result

    
    @SlowAPI.post('/control/task/{taskname}')
    def control_task(self, taskname:str, body:bytes):
        try:
            doc = json.loads(body.decode())
        except Exception as e:
            logging.error('control: JSON decoding error: %s' % str(e))
            return Response(400) # Bad Request
            
        action = doc.get('action', None)
        logging.info(f'Task Control: {taskname}.{action}()')
        
        for module in self.taskmodule_list:
            if module.name != taskname:
                continue
            if action == 'start':
                module.start()
                return {'status': 'ok'}
            elif action == 'stop':
                module.stop()
                return {'status': 'ok'}
            else:
                return { 'status': 'error', 'message': f'unknown command: {action}' }
            
        return { 'status': 'error', 'message': f'unknown task: {taskname}' }
