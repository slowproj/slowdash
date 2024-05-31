#! /usr/bin/env python3
# Created by Sanshiro Enomoto on 24 October 2022 #

import sys, os, time, io, logging, traceback
import importlib.machinery
import threading


class UserModuleThread(threading.Thread):
    def __init__(self, usermodule, params):
        threading.Thread.__init__(self)

        self.usermodule = usermodule
        self.params = params
        self.is_stop_requested = False
        
        
    def run(self):
        if not self.usermodule.load():
            return
            
        func_initialize = self.usermodule.get_func('_initialize')
        func_finalize = self.usermodule.get_func('_finalize')
        func_run = self.usermodule.get_func('_run')
        func_loop = self.usermodule.get_func('_loop')
        
        self.is_stop_requested = False

        if func_initialize:
            self.usermodule.routine_history.append((
                time.time(),
                '_initialize(%s)' % ','.join(['%s=%s' % (k,v) for k,v in self.params])
            ))
            try:
                func_initialize(self.params)
            except Exception as e:
                self.usermodule.handle_error('user module error: initialize(): %s' % str(e))
            
        if func_run:
            self.usermodule.routine_history.append((time.time(), 'run()'))
            try:
                func_run()
            except Exception as e:
                self.usermodule.handle_error('user module error: run(): %s' % str(e))
                
        if func_loop:
            self.usermodule.routine_history.append((time.time(), 'loop()'))
            while not self.is_stop_requested:
                try:
                    func_loop()
                    time.sleep(0.01)
                except Exception as e:
                    self.usermodule.handle_error('user module error: run(): %s' % str(e))
                    break
        
        if func_finalize:
            self.usermodule.routine_history.append((time.time(), 'finalize()'))
            try:
                func_finalize()
            except Exception as e:
                self.usermodule.handle_error('user module error: finalize(): %s' % str(e))



def input_waiting_at_EOF(prompt=None):
    if prompt:
        print(prompt)
    while True:
        try:
            return input()
        except EOFError:
            time.sleep(0.1)


                
class UserModule:        
    def __init__(self, filepath, name, params):
        self.filepath = filepath
        self.name = name
        self.params = params

        self.module = None
        self.user_thread = None

        if self.name is None:
            self.name = os.path.splitext(os.path.basename(self.filepath))[0]

        self.func_get_channels = None
        self.func_get_data = None
        self.func_process_command = None
        self.func_halt = None
        
        self.routine_history = []
        self.error = None

        
    def __del__(self):
        self.stop()

        
    def load(self):
        self.routine_history = []
        self.error = None
        
        if self.module is not None and False:  # ??? it look like just re-doing load() works...
            #??? this reload() does not execute statements outside a function
            print("=== Reloading %s ===" % self.filepath)
            try:
                self.module = importlib.reload(self.module)
            except Exception as e:
                self.handle_error('unable to reload user module: %s' % str(e))
                return False
        else:
            print("=== Loading %s ===" % self.filepath)
            if not os.path.exists(self.filepath):
                self.handle_error('unable to find user module: %s' % self.filepath)
                return False
            try:
                self.module = importlib.machinery.SourceFileLoader(self.name, self.filepath).load_module()
            except Exception as e:
                self.handle_error('unable to load user module: %s' % str(e))
                return False
                
        if self.module is None:
            return False

        self.func_get_channels = self.get_func('_get_channels')
        self.func_get_data = self.get_func('_get_data')
        self.func_process_command = self.get_func('_process_command')
        self.func_halt = self.get_func('_halt')

        if self.func_get_channels and self.func_get_data:
            logging.info('loaded user module data interface')
        if self.func_process_command:
            logging.info('loaded user module command processor')

        # Overriding the input() function to work with input from StringIO
        # BUG: this does not take affect while module loading (statements outside callback functions).
        # For now, use slowpy.ControlSystem.console().input() instead.
        self.module.__dict__['input'] = input_waiting_at_EOF

        logging.info('user module loaded: %s' % self.name)

        return True
        
    
    def start(self):
        self.stop()
        logging.info('starting user module "%s"' % self.name)
        
        self.user_thread = UserModuleThread(self, self.params)
        self.user_thread.start()
        
        
    def stop(self):
        if self.module is None or self.user_thread is None or not self.user_thread.is_alive():
            return
        
        logging.info('stoping user module "%s"' % self.name)

        self.user_thread.is_stop_requested = True
        if self.func_halt is not None:
            try:
                self.func_halt()
            except Exception as e:
                self.handle_error('user module error: halt(): %s' % str(e))

        if self.user_thread is not None:
            self.user_thread.join()
            self.user_thread = None

            
    def is_loaded(self):
        return self.module is not None

        
    def is_running(self):
        return self.user_thread is not None and self.user_thread.is_alive()


    def get_func(self, name):
        if self.module is None:
            return None
        if (name in self.module.__dict__) and callable(self.module.__dict__[name]):
            return self.module.__dict__[name]
        else:
            return None

        
    def get_channels(self):
        if self.module is None or self.func_get_channels is None:
            return None
        
        try:
            return self.func_get_channels()
        except Exception as e:
            self.handle_error('user module error: get_channels(): %s' % str(e))
            return None

    
    def get_data(self, channel):
        if self.module is None or self.func_get_data is None:
            return None
        
        try:
            return self.func_get_data(channel)
        except Exception as e:
            self.handle_error('user module error: get_data(): %s' % str(e))
            return None

    
    def process_command(self, params):
        if self.module is None or self.func_process_command is None:
            return None
        
        self.routine_history.append((
            time.time(),
            'process_command(%s)' % ','.join(['%s=%s' % (k,v) for k,v in params.items()])
        ))
        try:
            return self.func_process_command(params)
        except Exception as e:
            self.handle_error('user module error: process_command(): %s' % str(e))
            return {'status': 'error', 'message': str(e) }


    def handle_error(self, message):
        if self.error is None:
            self.error = message
            logging.error(message)
            logging.error(traceback.format_exc())
            print(message)
            print(traceback.format_exc())
    
        
    def clear_error(self):
        self.error = None
