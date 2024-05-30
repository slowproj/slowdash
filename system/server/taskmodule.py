#! /usr/bin/env python3
# Created by Sanshiro Enomoto on 24 May 2024 #

import time, logging, traceback
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

        logging.info('user task module loaded')
        
        
    def load(self):
        self.exports = None
        self.channel_list = None
        self.command_history = []
        
        return super().load()

        
    def stop(self):
        super().stop()
        
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
        
        func = self.get_func('export')
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
            self.exports[name] = node
            value = node.get()
            if type(value) == dict:
                if 'table' in value:
                    self.channel_list.append({'name': name, 'type': 'table'})
                else:
                    self.channel_list.append({'name': name, 'type': 'tree'})
            else:
                self.channel_list.append({'name': name})

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
        if self.func_process_command:
            return super().process_command(params)

        function_name, kwargs = None, {}
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
        if function_name is None or not function_name.startswith(self.name + '.'):
            return None
        function_name = function_name[len(self.name)+1:]
        
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
