#! /usr/bin/env python3
# Created by Sanshiro Enomoto on 24 October 2022 #

import sys, os, logging, traceback
import importlib.machinery


class UserModule:        
    def __init__(self, module, params):
        get_func = lambda name: (
            module.__dict__[name] if (name in module.__dict__ and callable(module.__dict__[name])) else None
        )
        self.func_get_channels = get_func('get_channel')
        self.func_get_data = get_func('get_data')
        self.func_process_command = get_func('process_command')
        self.func_initialize = get_func('initialize')
        self.func_finalize = get_func('finalize')
        
        if self.func_get_channels and self.func_get_data:
            logging.info('loaded user module data interface')
        if self.func_process_command:
            logging.info('loaded user module command processor')
                
        logging.info('user module loaded')
        
        if self.func_initialize:
            try:
                return self.func_initialize(params)
            except Exception as e:
                logging.error('user module error: %s' % str(e))
                logging.error(traceback.format_exc())


                
    def __del__(self):
        if self.func_finalize:
            try:
                return self.func_finalize()
            except Exception as e:
                logging.error('user module error: %s' % str(e))
                logging.error(traceback.format_exc())


                
    def get_channels(self):
        if self.func_get_channels:
            try:
                return self.func_get_channels()
            except Exception as e:
                logging.error('user module error: %s' % str(e))
                logging.error(traceback.format_exc())
        return None


    
    def get_data(self, channel):
        if self.func_get_data:
            try:
                return self.func_get_data(channel)
            except Exception as e:
                logging.error('user module error: %s' % str(e))
                logging.error(traceback.format_exc())
        return None

    
    
    def process_command(self, params):
        if not self.func_process_command:
            return None
        
        try:
            return self.func_process_command(params)
        except Exception as e:
            logging.error('user module error: %s' % str(e))
            logging.error(traceback.format_exc())
            return {'status': 'error', 'message': str(e) }


    
def load(filepath, project_config, params):
    if os.path.exists(filepath):
        module_name = os.path.splitext(os.path.basename(filepath))[0]
        try:
            module = importlib.machinery.SourceFileLoader(module_name, filepath).load_module()
        except Exception as e:
            logging.error('unable to load user module: %s' % str(e))
            logging.error(traceback.format_exc())
            return None

        module = UserModule(module, params)
        module.filepath = filepath

        return module
