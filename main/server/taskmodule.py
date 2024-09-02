#! /usr/bin/env python3
# Created by Sanshiro Enomoto on 24 May 2024 #

import os, time, logging, traceback
import threading
from usermodule import UserModule


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
        self.command_history = []
        self.namespace_prefix = params.get('namespace_prefix', '%s.' % name)
        self.namespace_suffix = params.get('namespace_suffix', '')

        self.control_system = None
        
        logging.info('user task module loaded')
        
        
    def _preset_module(self, module):
        super()._preset_module(module)

        # obtain a reference to the ControlSystem class in the user task module
        def register(control_system):
            self.control_system = control_system
            self.control_system._global_stop_event.clear()

        module.__dict__['_register'] = register
        try:
            exec("from slowpy.control import ControlSystem", module.__dict__)
            exec("_register(ControlSystem())", module.__dict__)
        except Exception as e:
            self.handle_error('unable to load user module: %s' % str(e))

        
    def load(self):
        self.exports = None
        self.channel_list = None
        self.command_history = []
        
        return super().load()

            
    def stop(self):
        super().stop()

        if self.control_system:
            logging.info('calling ControlSystem.stop() in UserTask "%s"' % self.name)
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

        value = self.exports[channel].get()
        if type(value) == dict:
            if 'tree' in value or 'table' in value:
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
        
        self.command_history.append((
            time.time(),
            '_process_command(%s)' % ','.join(['%s=%s' % (k,v) for k,v in params.items()])
        ))
        try:
            result = self.func_process_command(params)
        except Exception as e:
            self.handle_error('user module error: process_command(): %s' % str(e))
            return {'status': 'error', 'message': str(e) }

        return result
    

    def process_task_command(self, params):
        function_name, kwargs = '', {}
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
            else:
                kwargs[key] = value

        # task namespace
        if len(self.namespace_prefix) > 0:
            if not function_name.startswith(self.namespace_prefix):
                function_name = ''
            else:
                function_name = function_name[len(self.namespace_prefix):]
        if len(self.namespace_suffix) > 0:
            if not function_name.endswith(self.namespace_suffix):
                function_name = ''
            else:
                function_name = function_name[:-len(self.namespace_suffix)]
        if function_name.startswith('_'):
            function_name = ''
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
