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
        
        self.func_initialize = usermodule.get_func('initialize')
        self.func_finalize = usermodule.get_func('finalize')
        self.func_run = usermodule.get_func('run')
        self.func_loop = usermodule.get_func('loop')
        
        self.is_stop_requested = False

        
    def run(self):
        self.is_stop_requested = False

        if self.func_initialize:
            self.usermodule.routine_history.append((
                time.time(),
                'initialize(%s)' % ','.join(['%s=%s' % (k,v) for k,v in self.params])
            ))
            try:
                self.func_initialize(self.params)
            except Exception as e:
                logging.error('user module error: initialize(): %s' % str(e))
                logging.error(traceback.format_exc())
            
        if self.func_run:
            self.usermodule.routine_history.append((time.time(), 'run()'))
            try:
                self.func_run()
            except Exception as e:
                logging.error('user module error: run(): %s' % str(e))
                logging.error(traceback.format_exc())
        if self.func_loop:
            self.usermodule.routine_history.append((time.time(), 'loop()'))
            while not self.is_stop_requested:
                try:
                    self.func_loop()
                    time.sleep(0.01)
                except Exception as e:
                    logging.error('user module error: run(): %s' % str(e))
                    logging.error(traceback.format_exc())
                    break
        
        if self.func_finalize:
            self.usermodule.routine_history.append((time.time(), 'finalize()'))
            try:
                self.func_finalize()
            except Exception as e:
                logging.error('user module error: finalize(): %s' % str(e))
                logging.error(traceback.format_exc())

            
class UserModule:        
    def __init__(self, module, name, params, start_thread):
        self.module = module
        self.name = name

        self.func_get_channels = self.get_func('get_channels')
        self.func_get_data = self.get_func('get_data')
        self.func_process_command = self.get_func('process_command')
        self.func_halt = self.get_func('halt')

        if self.func_get_channels and self.func_get_data:
            logging.info('loaded user module data interface')
        if self.func_process_command:
            logging.info('loaded user module command processor')

        self.routine_history = []
            
        if start_thread:
            self.user_thread = UserModuleThread(self, params)
            self.user_thread.start()
        else:
            self.user_thread = None
            

    def __del__(self):
        if self.user_thread is not None:
            self.user_thread.join()
            logging.info('stopped user module run function')
            
                
    def is_running(self):
        return self.user_thread is not None and self.user_thread.is_alive()

        
    def get_func(self, name):
        if (name in self.module.__dict__) and callable(self.module.__dict__[name]):
            return self.module.__dict__[name]
        else:
            return None

        
    def halt(self):
        if self.user_thread is None or not self.user_thread.is_alive():
            return
        
        logging.info('stoping user module run function')
        self.user_thread.is_stop_requested = True
        if self.halt_func is not None:
            try:
                self.halt_func()
            except Exception as e:
                logging.error('user module error: halt(): %s' % str(e))
                logging.error(traceback.format_exc())


    def get_channels(self):
        if self.func_get_channels:
            try:
                return self.func_get_channels()
            except Exception as e:
                logging.error('user module error: get_channels(): %s' % str(e))
                logging.error(traceback.format_exc())
        return None

    
    def get_data(self, channel):
        if self.func_get_data:
            try:
                return self.func_get_data(channel)
            except Exception as e:
                logging.error('user module error: get_data(): %s' % str(e))
                logging.error(traceback.format_exc())
        return None

    
    def process_command(self, params):
        if not self.func_process_command:
            return None
        
        self.routine_history.append((
            time.time(),
            'process_command(%s)' % ','.join(['%s=%s' % (k,v) for k,v in params.items()])
        ))
        try:
            return self.func_process_command(params)
        except Exception as e:
            logging.error('user module error: process_command(): %s' % str(e))
            logging.error(traceback.format_exc())
            return {'status': 'error', 'message': str(e) }


    
def load(ModuleClass, filepath, name, params, start_thread):
    if os.path.exists(filepath):
        module_name = os.path.splitext(os.path.basename(filepath))[0]
        try:
            module = importlib.machinery.SourceFileLoader(module_name, filepath).load_module()
        except Exception as e:
            logging.error('unable to load user module: %s' % str(e))
            logging.error(traceback.format_exc())
            return None

        usermodule = ModuleClass(module, name, params, start_thread)
        usermodule.filepath = filepath

        return usermodule
