# Created by Sanshiro Enomoto on 24 October 2022 #

import sys, os, time, re, threading, asyncio, types, inspect, logging, traceback
import importlib.util

import slowlette
from sd_component import Component


class UserModuleThread(threading.Thread):
    def __init__(self, app, usermodule, user_params, stop_event):
        threading.Thread.__init__(self)

        self.app = app
        self.usermodule = usermodule
        self.user_params = user_params
        self.stop_event = stop_event
        self.initialized_event = threading.Event()
        self.loaded_event = threading.Event()
        self.eventloop = None

        
    def run(self):        
        self.eventloop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.eventloop)
        
        try:
            self.eventloop.run_until_complete(self.go())
        finally:
            # no "catch": propagate the error to make it visible for the user

            # stop all the pending tasks before closing the event loop
            pending_tasks = asyncio.all_tasks(self.eventloop)
            if len(pending_tasks) > 0:
                logging.info(f'UserModuleThread: cancelling pending tasks: {len(pending_tasks)} tasks')
                try:
                    for task in pending_tasks:
                        #logging.info(f'UserModuleThread: cancelling task: {task}')
                        task.cancel()
                    self.eventloop.run_until_complete(asyncio.gather(*pending_tasks, return_exceptions=True))
                except Exception as e:
                    logging.error(f'UserModuleThread: error on cancelling pending tasks: {e}')
                    
            # stop all the pending async generators
            try:
                self.eventloop.run_until_complete(self.eventloop.shutdown_asyncgens())
            except Exception as e:
                logging.error(f'UserModuleThread: error on cancelling async generators: {e}')
                
            self.eventloop.close()
            self.eventloop = None

        
    async def go(self):
        self.loaded_event.clear()
        self.initialized_event.clear()
        self.stop_event.clear()
        
        status = self.usermodule.load()
        self.loaded_event.set()
        if not status:
            return
        if self.stop_event.is_set():
            return
        
        func_setup = self.usermodule.get_func('_setup')
        func_initialize = self.usermodule.get_func('_initialize')
        func_run = self.usermodule.get_func('_run')
        func_loop = self.usermodule.get_func('_loop')
        func_finalize = self.usermodule.get_func('_finalize')

        if func_setup:
            nargs = len(inspect.signature(func_setup).parameters)
            if nargs >= 2:
                args = [ self.app, self.user_params ]
            elif nargs >= 1:
                args = [ self.app ]
            else:
                args = []                            
            try:
                if inspect.iscoroutinefunction(func_setup):
                    await func_setup(*args)
                else:
                    func_setup(*args)
            except Exception as e:
                self.usermodule.handle_error('user module error: _setup(): %s' % str(e))

        if func_initialize:
            self.usermodule.routine_history.append((
                time.time(),
                '_initialize(%s)' % ','.join(['%s=%s' % (k,v) for k,v in self.user_params.items()])
            ))
            nargs = len(inspect.signature(func_initialize).parameters)
            if nargs >= 1:
                args = [ self.user_params ]
            else:
                args = []
            try:
                if inspect.iscoroutinefunction(func_initialize):
                    await func_initialize(*args)
                else:
                    func_initialize(*args)
            except Exception as e:
                self.usermodule.handle_error('user module error: _initialize(): %s' % str(e))
            
        self.usermodule._do_post_initialize()
        self.initialized_event.set()
        
        if func_run and not self.stop_event.is_set():
            self.usermodule.routine_history.append((time.time(), '_run()'))
            try:
                if inspect.iscoroutinefunction(func_run):
                    await func_run()
                else:
                    func_run()
            except Exception as e:
                self.usermodule.handle_error('user module error: _run(): %s' % str(e))
            self.usermodule.routine_history.append((time.time(), '_run()'))
                
        if func_loop and not self.stop_event.is_set():
            self.usermodule.routine_history.append((time.time(), '_loop()'))
        while not self.stop_event.is_set():
            if func_loop:
                try:
                    if inspect.iscoroutinefunction(func_loop):
                        await func_loop()
                    else:
                        func_loop()
                except Exception as e:
                    self.usermodule.handle_error('user module error: _loop(): %s' % str(e))
                    func_loop = False
                await asyncio.sleep(0.01)
            else:
                # not to proceed to finalize() before a stop_event occurs
                await asyncio.sleep(0.1)
        if func_loop:
            self.usermodule.routine_history.append((time.time(), '_loop()'))
                
        if func_finalize:
            self.usermodule.routine_history.append((time.time(), '_finalize()'))
            try:
                if inspect.iscoroutinefunction(func_finalize):
                    await func_finalize()
                else:
                    func_finalize()
            except Exception as e:
                self.usermodule.handle_error('user module error: _finalize(): %s' % str(e))



class UserModule:        
    def __init__(self, app, filepath, name, params, user_params):
        self.app = app
        self.filepath = filepath
        self.name = name
        self.user_params = user_params

        self.module = None
        self.user_thread = None
        self.stop_event = threading.Event()

        self.func_get_channels = None
        self.func_get_data = None
        self.func_process_command = None
        self.func_halt = None
        self.slowlette = None

        self.func_get_html = None
        self.func_get_layout = None
        self.html_list = []
        self.layout_list = []
        
        self.routine_history = []
        self.command_history = []
        self.error = None
        self.is_waiting = False
        
        self.status_revision = int(time.time())
        self.was_running = False

        
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

            
    def _do_post_initialize(self):
        pass
    
        
    def load(self):
        self.routine_history = []
        self.command_history = []
        self.error = None

        # purge previously-loaded module tree (including submodules)
        if self.module is not None:
            to_del = [ k for k in sys.modules.keys() if k == self.name or k.startswith(self.name + '.') ]
            for k in to_del:
                sys.modules.pop(k, None)
            self.module = None
            
        self.touch_status()
        
        logging.debug("=== Loading %s ===" % self.filepath)
        if not os.path.exists(self.filepath):
            self.handle_error('unable to find user module: %s' % self.filepath)
            return False

        try:
            spec = importlib.util.spec_from_file_location(self.name, self.filepath)
            self.module = importlib.util.module_from_spec(spec)
            sys.modules[self.name] = self.module
        except Exception as e:
            self.handle_error('unable to load user module: %s' % str(e))
            self.module = None
            return False

        self._preset_module(self.module)
        
        try:
            spec.loader.exec_module(self.module)
        except Exception as e:
            self.handle_error('user module error: %s' % str(e))
            return False
                
        self.touch_status()
        logging.info('user module loaded: %s' % self.name)

        
        ### UserModule callbacks ###
        
        self.func_get_channels = self.get_func('_get_channels')
        self.func_get_data = self.get_func('_get_data')
        self.func_process_command = self.get_func('_process_command')
        self.func_halt = self.get_func('_halt')

        
        ### UserModule dynamic config contents (layout & HTML) ###
        
        self.func_get_html = self.get_func('_get_html')
        self.func_get_layout = self.get_func('_get_layout')
        
        if self.func_get_html is None:
            self.html_list = []
        else:
            func_get_html_list = self.get_func('_get_html_list')
            if func_get_html_list is None:
                self.html_list = [ self.name ]
            else:
                self.html_list = func_get_html_list()

        if self.func_get_layout is None:
            self.layout_layout = []
        else:
            func_get_layout_list = self.get_func('_get_layout_list')
            if func_get_layout_list is None:
                self.layout_list = [ self.name ]
            else:
                self.layout_list = func_get_layout_list()

                
        ### UserModule Web-API ###
        # To override SlowDash API, this is added as a middleware.
        # Note that UserModule.load() is called much later than App.__init__(), and can be called multiple times.
        if self.slowlette is not None:
            self.app.slowlette.remove_middleware(self.slowlette)
            self.slowlette = None
        for name, obj in self.module.__dict__.items():
            if isinstance(obj, slowlette.App) and name != '_slowdash_app':
                logging.info(f'loaded user module Web-API: {self.name}.{name}')
                self.slowlette = obj
                self.app.slowlette.add_middleware(obj)

                
        logging.debug('user module loaded: %s' % self.name)
        if self.func_get_channels and self.func_get_data:
            logging.debug('loaded user module data interface')
        if self.func_process_command:
            logging.debug('loaded user module command processor')

        return True
        
    
    async def start(self):
        self.touch_status()
        if self.module is not None and self.user_thread is not None and self.user_thread.is_alive():
            await self.stop()
        
        logging.info('starting user module: %s' % self.name)
        self.stop_event.clear()
        self.user_thread = UserModuleThread(self.app, self, self.user_params, self.stop_event)        
        self.touch_status()
        self.user_thread.start()
        
        for i in range(100):
            if not self.user_thread.loaded_event.is_set():
                await asyncio.sleep(0.1)
            else:
                break
            if i ==  10:
                logging.warning('User/Task module loading did not complete in one second. Still waiting...')
        else:
            logging.warning('User/Task module loading did not complete in 10 second')
        
        
    async def stop(self):
        if self.module is None or self.user_thread is None or not self.user_thread.is_alive():
            return
        
        logging.info('stopping user module "%s"' % self.name)
        self.touch_status()
        
        if not self.user_thread.initialized_event.is_set():
            logging.debug('stop before initialization completed')
            await asyncio.sleep(1)
            if not self.user_thread.initialized_event.is_set():
                logging.warning('User/Task module not yet initialized')
                
        self.touch_status()
        if self.func_halt is not None:
            try:
                if inspect.iscoroutinefunction(self.func_halt):
                    if self.user_thread.eventloop is not None:
                        future = asyncio.run_coroutine_threadsafe(
                            self.func_halt(),
                            self.user_thread.eventloop
                        )
                        result = future.result()
                    else:
                        await self.func_halt()
                else:
                    self.func_halt()
            except Exception as e:
                self.handle_error('user module error: halt(): %s' % str(e))
        self.stop_event.set()
        
        self.touch_status()
        if self.user_thread is not None:
            await asyncio.to_thread(self.user_thread.join, timeout=5)  # not to block the event loop during join()
            if self.user_thread.is_alive():
                self.handle_error('timeout on terminating a user thread')
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
        self.status_revision = int(time.time())
    

    def get_func(self, name):
        if self.module is None:
            return None
        if (name in self.module.__dict__) and callable(self.module.__dict__[name]):
            logging.debug(f'UserModule callback {name} found')
            return self.module.__dict__[name]
        else:
            logging.debug(f'UserModule callback {name} not defined')
            return None

        
    async def get_channels(self):
        if self.module is None or self.func_get_channels is None:
            return None
        
        if not self.user_thread.initialized_event.is_set():
            await asyncio.sleep(1)
            if not self.user_thread.initialized_event.is_set():
                logging.warning('User/Task module not yet initialized')
                
        try:
            if inspect.iscoroutinefunction(self.func_get_channels):
                channels = await self.func_get_channels()
            else:
                channels = self.func_get_channels()
        except Exception as e:
            self.handle_error('user module error: get_channels(): %s' % str(e))
            return None

        for ch in channels:
            ch['current'] = True

        return channels
    
    
    async def get_data(self, channel):
        if self.module is None or self.func_get_data is None:
            return None
        
        if not self.user_thread.initialized_event.is_set():
            await asyncio.sleep(1)
            if not self.user_thread.initialized_event.is_set():
                logging.warning('User/Task module not yet initialized')
                
        try:
            if inspect.iscoroutinefunction(self.func_get_data):
                return await self.func_get_data(channel)
            else:
                return self.func_get_data(channel)
        except Exception as e:
            self.handle_error('user module error: get_data(): %s' % str(e))
            return None

    
    async def process_command(self, params):
        if self.module is None or self.func_process_command is None:
            return None
        
        if not self.user_thread.initialized_event.is_set():
            await asyncio.sleep(1)
            if not self.user_thread.initialized_event.is_set():
                logging.warning('User/Task module not yet initialized')
                
        try:
            self.touch_status()
            if inspect.iscoroutinefunction(self.func_process_command):
                if self.user_thread.eventloop is not None:
                    future = asyncio.run_coroutine_threadsafe(
                        self.func_process_command(params),
                        self.user_thread.eventloop
                    )
                    result = future.result()
                else:
                    result = await self.func_process_command(params)
            else:
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
            

    async def get_contentlist(self):
        result = []
        
        for content_type, file_ext, content_list in [
            ('html', 'html', self.html_list),
            ('slowplot', 'json', self.layout_list),
        ]:
            for name in content_list:
                entry = {
                    'type': content_type,
                    'name': name,
                    'config_file': f'{content_type}-{name}.{file_ext}',
                    'description': f'dynamic {content_type} from UserModule {self.name}',
                }
                result.append(entry)
                
        return result

    
    async def get_content(self, filename:str):
        content_type, content = None, None
        if self.module is None:
            return content_type, content

        if filename.startswith('html-'):
            pattern = r'html-([a-zA-Z0-9_\-]+)(\.html)?'
            content_type = 'text/html'
            is_html = True
        elif filename.startswith('slowplot-'):
            pattern = r'slowplot-([a-zA-Z0-9_\-]+)(\.json)?'
            content_type = 'text/json'
            is_html = False
        else:
            return content_type, content
        
        match = re.fullmatch(pattern, filename)
        if not match:
            return content_type, content
        content_name = match.group(1)

        func_get_content = None
        if is_html:
            if content_name in self.html_list:
                func_get_content = self.func_get_html
        else:
            if content_name in self.layout_list:
                func_get_content = self.func_get_layout
        if func_get_content is None:
            return content_type, content

        nargs = len(inspect.signature(func_get_content).parameters)
        if nargs >= 1:
            args = [ content_name ]
        else:
            args = []
            
        try:
            if inspect.iscoroutinefunction(func_get_content):
                content = await func_get_content(*args)
            else:
                content = func_get_content(*args)
        except Exception as e:
            self.handle_error('user module error: get_content(): %s' % str(e))
            content = None

        return content_type, content
    

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

        self.usermodule_list = {}
        
        usermodule_node = self.project.config.get('module', None)
        if usermodule_node is None:
            usermodule_node = self.project.config.get('modules', [])  # suger added...
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
            name = node.get('name', os.path.splitext(os.path.basename(filepath))[0])
            user_params = node.get('parameters', {})
            module = UserModule(self.app, filepath, name, node, user_params)
            if module is None:
                logging.error('Unable to load user module: %s' % filepath)
                continue

            if name not in self.usermodule_list:
                self.usermodule_list[name] = module
            else:
                for i in range(2, 100):
                    new_name = f"{name}__{i}"
                    if new_name not in self.usermodule_list:
                        self.usermodule_list[new_name] = module
                        logging.warn(f'Instance {i} of user module "{name}" is renamed to {new_name}')
                else:
                    logging.error(f'Too many user modules of the same name: {name}')


    @slowlette.on_event('startup')
    async def startup(self):
        await asyncio.gather(*(module.start() for module in self.usermodule_list.values()))


    @slowlette.on_event('shutdown')
    async def shutdown(self):
        await asyncio.gather(*(module.stop() for module in self.usermodule_list.values()))
            
        if len(self.usermodule_list) > 0:
            logging.info('user modules terminated')
            
        self.usermodule_list = {}
        
    
    def public_config(self):
        if len(self.usermodule_list) == 0:
            return None
        
        return {
            'user_module': {
                name: {} for name in self.usermodule_list.keys()
            }
        }


    @slowlette.get('/api/channels')
    async def api_channels(self):
        result = []
        for usermodule in self.usermodule_list.values():
            result.extend(await usermodule.get_channels() or [])
            
        return result

        
    @slowlette.get('/api/data/{channels}')
    async def api_data(self, channels:str, opts:dict):
        if len(self.usermodule_list) == 0:
            return None
        
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
        start = (to if to > 0 else now + to) - length

        result = {}
        for usermodule in self.usermodule_list.values():
            for ch in channels:
                data = await usermodule.get_data(ch)
                if data is not None:
                    result[ch] = {
                        'start': start, 'length': length,
                        't': now - start,
                        'x': data
                    }

        return result

    
    @slowlette.post('/api/control')
    async def post_control(self, doc:slowlette.DictJSON):
        logging.info(f'Command: {doc}')
        if len(self.usermodule_list) == 0:
            return None
        
        # unlike GET, only one module can process to POST
        for module in self.usermodule_list.values():
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


    @slowlette.get('/api/config/contentlist')
    async def get_usermodule_contentlist(self):
        result = []
        for usermodule in self.usermodule_list.values():
            result.extend(await usermodule.get_contentlist())
                
        return result

        
    @slowlette.get('/api/config/content/{filename}')
    async def get_usermodule_content(self, filename:str):
        for usermodule in self.usermodule_list.values():
            content_type, content = await usermodule.get_content(filename)
            if content is not None:
                return slowlette.Response(200, content_type=content_type, content=content)
            
        return None
