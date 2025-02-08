# Created by Sanshiro Enomoto on 24 October 2022 #

import sys, os, time, threading, types, logging, traceback
import importlib.machinery

import slowapi
from sd_component import Component


class UserModuleThread(threading.Thread):
    def __init__(self, usermodule, params, stop_event):
        threading.Thread.__init__(self)

        self.usermodule = usermodule
        self.params = params
        self.stop_event = stop_event
        self.initialized_event = threading.Event()
        
        
    def run(self):
        self.initialized_event.clear()
        self.stop_event.clear()
        if not self.usermodule.load():
            return
        if self.stop_event.is_set():
            return
        
        func_initialize = self.usermodule.get_func('_initialize')
        func_run = self.usermodule.get_func('_run')
        func_loop = self.usermodule.get_func('_loop')
        func_finalize = self.usermodule.get_func('_finalize')
        
        if func_initialize:
            self.usermodule.routine_history.append((
                time.time(),
                '_initialize(%s)' % ','.join(['%s=%s' % (k,v) for k,v in self.params.items()])
            ))
            try:
                func_initialize(self.params)
            except Exception as e:
                self.usermodule.handle_error('user module error: _initialize(): %s' % str(e))
            
        self.initialized_event.set()
        
        if func_run and not self.stop_event.is_set():
            self.usermodule.routine_history.append((time.time(), '_run()'))
            try:
                func_run()
            except Exception as e:
                self.usermodule.handle_error('user module error: _run(): %s' % str(e))
                
        if func_loop and not self.stop_event.is_set():
            self.usermodule.routine_history.append((time.time(), '_loop()'))
            while not self.stop_event.is_set():
                try:
                    func_loop()
                    time.sleep(0.01)
                except Exception as e:
                    self.usermodule.handle_error('user module error: _loop(): %s' % str(e))
                    break

        if func_finalize:
            self.usermodule.routine_history.append((time.time(), '_finalize()'))
            try:
                func_finalize()
            except Exception as e:
                self.usermodule.handle_error('user module error: _finalize(): %s' % str(e))



class UserModule:        
    def __init__(self, filepath, name, params):
        self.filepath = filepath
        self.name = name
        self.params = params

        self.module = None
        self.user_thread = None
        self.stop_event = threading.Event()

        if self.name is None:
            self.name = os.path.splitext(os.path.basename(self.filepath))[0]

        self.func_get_channels = None
        self.func_get_data = None
        self.func_process_command = None
        self.func_halt = None
        
        self.routine_history = []
        self.command_history = []
        self.error = None
        self.is_waiting = False
        
        self.status_revision = 1
        self.was_running = False

        
    def __del__(self):
        self.stop()

        
    def _preset_module(self, module):
        # Overriding the input() function to work with input from StringIO
        def input_waiting_at_EOF(prompt=None):
            if prompt:
                print(prompt)
            self.is_waiting = True
            self.touch_status()
            while True:
                if self.stop_event.is_set():
                    line = ''
                    break
                try:
                    line = input()
                    break
                except EOFError:
                    time.sleep(0.1)
                    
            self.is_waiting = False
            self.touch_status()
            return line

        module.__dict__['input'] = input_waiting_at_EOF
        
        
    def load(self):
        self.routine_history = []
        self.command_history = []
        self.error = None
        self.touch_status()
        
        if self.module is not None and False:  #??? it looks like just re-doing load() works...
            #??? this reload() does not execute statements outside a function
            logging.debug("=== Reloading %s ===" % self.filepath)
            self._preset_module(self.module)
            try:
                self.module = importlib.reload(self.module)
            except Exception as e:
                self.handle_error('unable to reload user module: %s' % str(e))
                return False
            
        else:
            logging.debug("=== Loading %s ===" % self.filepath)
            if not os.path.exists(self.filepath):
                self.handle_error('unable to find user module: %s' % self.filepath)
                return False

            # use a dummy module with the same name as the user module:
            # entries in the dummy modules will remain after loading the user module
            dummy_module = types.ModuleType(self.name)
            self._preset_module(dummy_module)
            sys.modules[self.name] = dummy_module
            
            try:
                self.module = importlib.machinery.SourceFileLoader(self.name, self.filepath).load_module()
            except Exception as e:
                self.handle_error('unable to load user module: %s' % str(e))
                return False
                
        self.touch_status()
        if self.module is None:
            return False

        self.func_get_channels = self.get_func('_get_channels')
        self.func_get_data = self.get_func('_get_data')
        self.func_process_command = self.get_func('_process_command')
        self.func_halt = self.get_func('_halt')

        logging.debug('user module loaded: %s' % self.name)
        if self.func_get_channels and self.func_get_data:
            logging.debug('loaded user module data interface')
        if self.func_process_command:
            logging.debug('loaded user module command processor')

        return True
        
    
    def start(self):
        self.touch_status()
        if self.module is not None and self.user_thread is not None and self.user_thread.is_alive():
            self.stop()
        
        logging.info('starting user module "%s"' % self.name)
        self.stop_event.clear()
        self.user_thread = UserModuleThread(self, self.params, self.stop_event)
        self.touch_status()
        self.user_thread.start()
        
        
    def stop(self):
        if self.module is None or self.user_thread is None or not self.user_thread.is_alive():
            return
        
        logging.info('stopping user module "%s"' % self.name)
        self.touch_status()
        
        if not self.user_thread.initialized_event.is_set():
            time.sleep(1)
            if not self.user_thread.initialized_event.is_set():
                logging.warning('User/Task module not yet initialized')
                
        self.touch_status()
        if self.func_halt is not None:
            try:
                self.func_halt()
            except Exception as e:
                self.handle_error('user module error: halt(): %s' % str(e))
        self.stop_event.set()
        
        self.touch_status()
        if self.user_thread is not None:
            self.user_thread.join()
            self.user_thread = None
            
        self.touch_status()

            
    def is_loaded(self):
        return self.module is not None

        
    def is_running(self):
        self.was_running = self.user_thread is not None and self.user_thread.is_alive()
        return self.was_running


    def is_waiting_input(self):
        return self.is_waiting


    def is_stopped(self):
        return self.stop_event.is_set()


    def touch_status(self):
        self.status_revision += 1  # note: there is no limit on int in Python3
    

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
        
        if not self.user_thread.initialized_event.is_set():
            time.sleep(1)
            if not self.user_thread.initialized_event.is_set():
                logging.warning('User/Task module not yet initialized')
                
        try:
            return self.func_get_channels()
        except Exception as e:
            self.handle_error('user module error: get_channels(): %s' % str(e))
            return None

    
    def get_data(self, channel):
        if self.module is None or self.func_get_data is None:
            return None
        
        if not self.user_thread.initialized_event.is_set():
            time.sleep(1)
            if not self.user_thread.initialized_event.is_set():
                logging.warning('User/Task module not yet initialized')
                
        try:
            return self.func_get_data(channel)
        except Exception as e:
            self.handle_error('user module error: get_data(): %s' % str(e))
            return None

    
    def process_command(self, params):
        if self.module is None or self.func_process_command is None:
            return None
        
        if not self.user_thread.initialized_event.is_set():
            time.sleep(1)
            if not self.user_thread.initialized_event.is_set():
                logging.warning('User/Task module not yet initialized')
                
        try:
            self.touch_status()
            result = self.func_process_command(params)
            self.touch_status()
        except Exception as e:
            self.handle_error('user module error: process_command(): %s' % str(e))
            return {'status': 'error', 'message': str(e) }

        if result is not None:
            self.command_history.append((
                time.time(),
                'process_command(%s)' % ','.join(['%s=%s' % (k,v) for k,v in params.items()])
            ))

        return result
            

    def handle_error(self, message):
        if self.error is None:
            self.error = message

            # print() for web console
            logging.error(message)
            print(message)

            if sys.exc_info()[0] is not None:
                tb = traceback.format_exc()
                if tb is not None and len(tb.strip()) > 0:
                    logging.info(tb)
                    print(tb)
    
        
    def clear_error(self):
        self.error = None



class UserModuleComponent(Component):
    def __init__(self, app, project):
        super().__init__(app, project)

        self.usermodule_list = []
        
        usermodule_node = self.project.config.get('module', [])
        if not isinstance(usermodule_node, list):
            usermodule_node = [ usermodule_node ]
            
        for node in usermodule_node:
            if not isinstance(node, dict) or 'file' not in node:
                logging.error('bad user module configuration')
                continue
            if app.is_cgi and node.get('enabled_for_cgi', False) != True:
                continue
            if app.is_command and node.get('enabled_for_commandline', True) != True:
                continue
            filepath = node['file']
            params = node.get('parameters', {})
            module = UserModule(filepath, filepath, params)
            if module is None:
                logging.error('Unable to load user module: %s' % filepath)
            else:
                self.usermodule_list.append(module)

        for module in self.usermodule_list:
            module.start()


    @slowapi.on_event('shutdown')
    def finalize(self):
        for module in self.usermodule_list:
            module.stop()
            
        if len(self.usermodule_list) > 0:
            logging.info('user modules terminated')
            
        self.usermodule_list = []
        
    
    def public_config(self):
        if len(self.usermodule_list) == 0:
            return None
        
        return {
            'user_module': {
                module.name: {} for module in self.usermodule_list
            }
        }


    @slowapi.get('/channels')
    def get_channels(self):
        result = []
        for usermodule in self.usermodule_list:
            channels = usermodule.get_channels()
            if channels is not None:
                result.extend(channels)
        return result

        
    @slowapi.get('/data/{channels}')
    def get_data(self, channels:str, opts:dict):
        if len(self.usermodule_list) == 0:
            return None
        
        try:
            channels = channels.split(',')
            length = float(opts.get('length', '3600'))
            to = float(opts.get('to', int(time.time())+1))
        except Exception as e:
            logging.error('Bad data URL: %s: %s' % (str(opts), str(e)))
            return False
        
        has_result, result = False, {}
        start = to - length
        t = time.time() - start
        if t >= 0 and t <= length + 10:
            for usermodule in self.usermodule_list:
                for ch in channels:
                    data = usermodule.get_data(ch)
                    if data is None:
                        continue
                    has_result = True
                    result[ch] = {
                        'start': start, 'length': length,
                        't': t,
                        'x': data
                    }

        return result if has_result else None

    
    @slowapi.post('/control')
    def post_control(self, doc:slowapi.DictJSON):
        if len(self.usermodule_list) == 0:
            return None
        
        # unlike GET, only one module can process to POST
        for module in self.usermodule_list:
            result = module.process_command(dict(doc))
            if result is not None:
                logging.info(f'UserModule Command: {doc}')
                break
        else:
            return None

        if type(result) is bool:
            if result:
                return {'status': 'ok'}
            else:
                return {'status': 'error'}
        elif type(result) is int:
            return slowapi.Response(result)

        return result
