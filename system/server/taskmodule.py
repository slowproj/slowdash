#! /usr/bin/env python3
# Created by Sanshiro Enomoto on 24 May 2024 #

import logging, traceback
import threading
from usermodule import UserModule


class TaskFunctionThread(threading.Thread):
    def __init__(self, func, kwargs):
        super().__init__()
        self.func = func
        self.kwargs = kwargs

    def run(self):
        self.func(**self.kwargs)


        
class TaskModule(UserModule):
    def __init__(self, module, params):
        super().__init__(module, params)
        self.thread = None

        logging.info('user task module loaded')
        
        
    def __del__(self):
        if self.thread is not None:
            if self.thread.is_alive():
                #kill
                pass
            thread.join()
        super().__del__()
        

    def is_running(self):
        return self.thread is not None and self.thread.is_alive()

        
    def process_command(self, params):
        if self.func_process_command:
            return super().process_command(params)

        function_name, kwargs = None, {}
        for key, value in params.items():
            if len(key) > 2 and key.endswith('()'):
                function_name = key[:-2]
            else:
                kwargs[key] = value
        if function_name is None:
            return super().process_command(params)
            
        if self.thread is not None:
            if self.thread.is_alive():
                return {'status': 'error', 'message': 'script already running'}
            else:
                self.thread.join()
        
        func = self._get_func(function_name)
        if func is None:
            return {'status': 'error', 'message': 'undefined function: %s' % function_name}
        
        self.thread = TaskFunctionThread(func, kwargs)
        self.thread.start()
                
        return True
