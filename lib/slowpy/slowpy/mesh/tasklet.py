# Created by Sanshiro Enomoto on 13 August 2025 #

import sys, time, copy, json, asyncio, inspect, traceback, logging
from datetime import datetime, timezone
from pathlib import Path

from slowpy.control import control_system as ctrl

from .mesh import Mesh
from .stdio import MeshStdio
from .dash import Dash



class Tasklet:
    def __init__(self, name:str|None=None, *, use_oldstyle_callbacks=False, mesh_stdio=True):
        self._name = name
        self._use_oldstyle_callbacks = use_oldstyle_callbacks
        
        self._params = {}
        
        self._dash_url = None
        self._dash = Dash()
        
        self._mesh_url = None
        self._mesh = Mesh(name=name, on_reconnect=self.on_reconnect, name_prefix_to_drop='slowtask-')
        
        if mesh_stdio:
            self._mesh_stdio = MeshStdio(self._mesh, topic_prefix='sd.task')
        else:
            self._mesh_stdio = None
        
        self._mesh_list = [ self._mesh ]
        self._initialize_task_coros = []
        self._main_task_coros = []
        self._finalize_task_coros = []

        self._heartbeat_interval = 5
        self._next_heartbeat_time = 0

        self._content_generators = {}
        
        
    @property
    def name(self):
        return self._name

    @property
    def mesh(self):
        return self._mesh

    @property
    def dash(self):
        return self._dash

        
    def external_mesh(self, mesh_url:str, **kwargs):
        """returns a mesh object to communicate with an external SlowMesh
        -  This mesh will be started and stopped together with the main mesh.
        """
        mesh = Mesh(mesh_url, **kwargs)
        self._mesh_list.append(mesh)
        return mesh


    def run(self, params:dict|None=None, *, slowdash_url:str|None=None, mesh_url:str|None=None, name:str|None=None, module=None):
        self._params = copy.deepcopy(params)
        self._dash_url = slowdash_url or self._dash_url
        self._mesh_url = mesh_url or self._mesh_url
        if self._mesh_url is None and self._dash_url is not None:
            if self._dash_url.startswith('http://'):
                self._mesh_url = 'slowmq' + self._dash_url[4:]
            elif self._dash_url.startswith('https://'):
                self._mesh_url = 'slowmqs' + self._dash_url[5:]

        if name is not None:
            self._name = name
        if module is None:
            caller_frame = inspect.currentframe().f_back
            modname = caller_frame.f_globals.get('__name__')
            module = sys.modules.get(modname)
        if module is None:
            logging.error(f'Tasklet: unable to get module: {modname}')

        if self._use_oldstyle_callbacks:
            self._scan_oldstyle_callbacks(module)

        self._export_content_generators()
            
        ctrl.stop_by_signal()
        try:
            asyncio.run(self._start())
        except asyncio.CancelledError:
            pass
            

    def is_stop_requested(self):
        return ctrl.is_stop_requested()
    

    #### Callback Decorators ####
        
    def initialize(self):
        """decorator to add a tasklet initialization task
        """
        def wrapper(func):
            self._add_initialize_callback(func)
            return func
        return wrapper
        
        
    def finalize(self):
        """decorator to add a tasklet finalization task
        """
        def wrapper(func):
            self._add_finalize_callback(func)
            return func
        return wrapper
        
        
    def once(self, delay:float=0):
        """decorator to add a tasklet task
        """
        def wrapper(func):
            self._add_once_callback(func, delay)
            return func
        return wrapper
        

    def loop(self, interval:float=0, *, ticks:None|int|dict[str,int]=None):
        """decorator to add a tasklet task
        """
        def wrapper(func):
            self._add_loop_callback(func, interval, ticks=ticks)
            return func
        return wrapper
        

    def schedule(self, time_list:str, *, use_utc:bool=False):
        """decorator to add a tasklet task
        Args:
        time_list: comma-separated list of times in HH:MM. HH and MM must be an integer or *.
        use_utc: set True to use the UTC time.
        """
        def wrapper(func):
            self._add_schedule_callback(func, time_list, use_utc)
            return func
        return wrapper
        

    #### Other Decorators ####

    def content(self, name:str, *, content_type:str|None=None):
        """decorator to declare a content generator
        Args:
        name (str): name of the content, e.g., "config/html-mytask" / "config/slowplot-mytask"
        content_type (str|None): content MIME type; None for automatically detect from the name
        """
        def wrapper(func):
            self._content_generators[name] = (content_type, func)
            func._slowpy_task = True
            return func
        return wrapper

    
    #### Internal Methods ####

    def _scan_oldstyle_callbacks(self, module):
        if module is None:
            return
        
        def _get_func(name):
            if (name in module.__dict__) and callable(module.__dict__[name]):
                func = module.__dict__[name]
                if hasattr(func, '_slowpy_task'):
                    logging.debug(f'Tasklet callback {name} has a callback decorator: skipped')
                    return None
                else:
                    logging.debug(f'Tasklet callback {name} found')
                    return func
            else:
                logging.debug(f'Tasklet callback {name} not defined')
                return None

        func_initialize = _get_func('_initialize')
        if func_initialize:
            self._add_initialize_callback(func_initialize)
            
        func_finalize = _get_func('_finalize')
        if func_finalize:
            self._add_finalize_callback(func_finalize)
        
        func_run = _get_func('_run')
        if func_run:
            if not inspect.iscoroutinefunction(func_run):
                # non-async function will stop all the other async tasks
                logging.warning(f'Tasklet: _run() callback must be async; otherwise other functions will not be called')
            self._add_once_callback(func_run)
                
        func_loop = _get_func('_loop')
        if func_loop:
            if not inspect.iscoroutinefunction(func_loop):
                # use of time.sleep() in user function will cause starving
                logging.warning(f'Tasklet: _loop() callback must be async; a loop delay of 0.1 sec is inserted')
                loop_delay = 0.1
            else:
                loop_delay = 0
            self._add_loop_callback(func_loop, loop_delay)

        for name, func in module.__dict__.items():
            if name.startswith('_'):
                continue
            if not inspect.isfunction(func):  # alternatively, "not callable(func)" for a wider scope
                continue
            if func.__module__ != module.__name__:
                continue
            if hasattr(func, '_slow_task'):
                continue
            self._mesh.export(name, func)


    def _export_content_generators(self):
        async def handle_get_content(name:str):
            content_type, func = self._content_generators.get(name)
            if func is None:
                return None
            return func()

        self._mesh.export('_sd_get_content', handle_get_content)


    async def _start(self):
        if self._dash_url is not None:
            self._dash.connect(self._dash_url)
        if self._mesh_url is not None:
            self._mesh.connect(self._mesh_url, name=self._name)
            if self._name is None:
                self._name = self._mesh.name

        if self._mesh_stdio is not None and self._mesh_url is not None:
            await self._mesh_stdio.aio_start()
        
        for mesh in self._mesh_list:
            await mesh.aio_start()   

        try:
            await asyncio.gather(*self._initialize_task_coros)
        except Exception as e:
            if self._mesh_stdio is not None:
                await self._mesh_stdio.aio_stop()
            for mesh in self._mesh_list:
                try:
                    await mesh.aio_close()   
                except Exception:
                    pass
            try:
                await self._dash.aio_close()
            except Exception:
                pass
            raise e

        async def handle_control(headers, data):
            if headers.get('topic', '') == 'sd.task.control.introduce':
                await self._publish_spec()
        await self.mesh.aio_subscribe('sd.task.control.>', handle_control)
        await self._publish_spec()

        main_tasks = set()
        try:
            for coro in self._main_task_coros:
                task = asyncio.create_task(coro)
                task.add_done_callback(main_tasks.discard)
                main_tasks.add(task)
            while not ctrl.is_stop_requested():
                await self._heartbeat()   # doing this in the main loop (not coro) to ensure it stops with the main
                await ctrl.aio_sleep(0.1)
        except Exception as e:
            raise e    
        
        finally:
            try:
                await self._publish_exit()
            except Exception as e:
                print(e)
                pass
            except:
                pass
                
            while main_tasks:
                task = main_tasks.pop()
                try:
                    task.cancel()
                    await task
                except Exception as e:
                    logging.error(f'Tasklet: error during clean up: {e}')
                except:
                    pass
            
            try:
                await asyncio.gather(*self._finalize_task_coros)
            except Exception as e:
                self._handle_error(f'error during clean up: {e}')
            except:
                pass

            if self._mesh_stdio is not None:
                await self._mesh_stdio.aio_stop()
            for mesh in self._mesh_list:
                try:
                    await mesh.aio_close()
                except Exception:
                    pass
            try:
                await self._dash.aio_close()
            except Exception:
                pass


    async def on_reconnect(self):
        await self._publish_spec()

        
    async def _publish_spec(self):
        functions = {}
        for func_name, func in self.mesh.export_functions().items():
            if len(func_name) == 0 or not func_name[0].isalpha():
                continue
            
            signature = inspect.signature(func)
            kwargs, arbitrary_keywords, has_non_pod = {}, False, False
            for arg_name, attr in signature.parameters.items():
                if attr.kind == inspect.Parameter.VAR_KEYWORD:
                    arbitrary_keywords = True
                    continue
                
                kwargs[arg_name] = {}
                arg_type = None
                if attr.annotation is not inspect.Parameter.empty:
                    arg_type = attr.annotation
                elif attr.default is not inspect.Parameter.empty and attr.default is not None:
                    arg_type = type(attr.default)
                if arg_type in (int, float, str, bool):
                    kwargs[arg_name]['type'] = arg_type.__name__
                    if attr.default is not inspect.Parameter.empty:
                        kwargs[arg_name]['default'] = attr.default
                else:
                    has_non_pod = True

            if not has_non_pod:
                functions[func_name] = {
                    'kwargs': kwargs,
                    'arbitrary_keywords': arbitrary_keywords
                }

        variables = {}
        for var_name, var in self.mesh.export_variables().items():
            variables[var_name] = { 'type': 'control_node' }
            try:
                value = await var.aio_get()
            except Exception:
                continue
            
            try:
                _ = json.dumps(value)
                variables[var_name]['probe_value'] = value
            except Exception:
                pass
            
            if isinstance(value, (int, float)):
                variables[var_name]['data_type'] = 'numeric'
            elif isinstance(value, str):
                variables[var_name]['data_type'] = 'string'
            elif isinstance(value, dict):
                if 'tree' in value:
                    variables[var_name]['data_type'] = 'tree'
                elif 'bins' in value:
                    variables[var_name]['data_type'] = 'histogram'
                elif 'y' in value:
                    variables[var_name]['data_type'] = 'graph'
                elif 'table' in value:
                    variables[var_name]['data_type'] = 'table'

        contents = {}
        for name, (content_type, func) in self._content_generators.items():
            if content_type is None:
                ext = Path(name).suffix
                if ext == '.html':
                    content_type = 'text/html'
                elif ext == '.json':
                    content_type = 'application/json'
                elif ext == '.yaml':
                    content_type = 'application/yaml'
                else:
                    content_type = 'application/octet-stream'
            contents[name] = { 'content_type': content_type }
                    
        spec_doc = {
            'mesh_id': self.mesh.mesh_id,
            'name': self.name,
            'timestamp': time.time(),
            'functions': functions,
            'variables': variables,
            'contents': contents,
        }
        if self._mesh_stdio:
            spec_doc['stdio'] = self._mesh_stdio.spec        
        
        await self.mesh.aio_publish(f'sd.task.spec.{self.name}.{self.mesh.mesh_id}', spec_doc)
        
        
    async def _publish_exit(self):
        doc = {
            'mesh_id': self.mesh.mesh_id,
            'name': self.name,
            'timestamp': time.time()
        }
        await self.mesh.aio_publish(f'sd.task.exit.{self.name}.{self.mesh.mesh_id}', doc)

        
    async def _heartbeat(self):
        now = time.time()
        if now > self._next_heartbeat_time:
            self._next_heartbeat_time = now + self._heartbeat_interval
            headers = {
                'mesh_id': self.mesh.mesh_id,
                'name': self.name,
                'timestamp': now
            }
            body = {
                'expire': int(self._next_heartbeat_time) + 1
            }
            await self.mesh.aio_publish(f'sd.task.heartbeat.{self.name}.{self.mesh.mesh_id}', body, headers=headers)

    
    def _add_initialize_callback(self, func):
        """
        Args:
          func: callback function
        """
        async def go_initialize():
            nargs = len(inspect.signature(func).parameters)
            if nargs >= 1:
                args = [ self._params ]
            else:
                args = []
            try:
                result = func(*args)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                self._handle_error(f'Tasklet error: {func.__name__}(): {e}')

        func._slowpy_task = True
        self._initialize_task_coros.append(go_initialize())

                
    def _add_finalize_callback(self, func):
        """
        Args:
          func: callback function
        """
        async def go_finalize():
            try:
                result = func()
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                self._handle_error(f'Tasklet error: {func.__name__}(): {e}')

        func._slowpy_task = True
        self._finalize_task_coros.append(go_finalize())

                
    def _add_once_callback(self, func, delay:float):
        """
        Args:
          func: callback function
          delay: func execution delay after completion of intialization
        """
        func._slowpy_task = True
        async def go_once():
            try:
                start = time.monotonic()
                while not ctrl.is_stop_requested():
                    now = time.monotonic()
                    if now - start < delay:
                        await asyncio.sleep(0.1)
                        continue
                    
                    result = func()
                    if asyncio.iscoroutine(result):
                        await result
                    else:
                        await asyncio.sleep(0.01)
                    break
            except Exception as e:
                self._handle_error(f'Tasklet error: {func.__name__}(): {e}')
                
        self._main_task_coros.append(go_once())

                
    def _add_loop_callback(self, func, interval:float, *, ticks:None|int|dict[str,int]=None):
        """
        Args:
          func: callback function
          interval: func execution intervals. Zero for no wait, negative to run the func only once.
          ticks (None|int|dict[str|int]): if set, callback receives tick flag(s) (True on every ticks loop interations)
        """
        class TickFlags(dict):
            def __getattr__(self, name):
                try:
                    return self[name]
                except KeyError:
                    raise AttributeError(name) from None

        def make_tick_flags(tick_count):
            if ticks is None:
                return None
            if isinstance(ticks, dict):
                return TickFlags({ name: tick_count % int(period) == 0 for name, period in ticks.items() })
            
            return tick_count % ticks == 0
                    

        
        async def go_loop():
            try:
                last_execusion_time = time.monotonic()
                tick_count = 0
                while not ctrl.is_stop_requested():
                    ticks_elapsed = 1
                    if interval > 0:
                        now = time.monotonic()
                        lapse = now - last_execusion_time
                        if lapse < interval:
                            await asyncio.sleep(min(interval-lapse, 0.5))
                            continue
                        ticks_elapsed = int(lapse / interval)
                        last_execusion_time += ticks_elapsed * interval
                    tick_count += ticks_elapsed

                    if ticks is None:
                        result = func()
                    else:
                        result = func(make_tick_flags(tick_count))
                        
                    if asyncio.iscoroutine(result):
                        await result
                    else:
                        await asyncio.sleep(0.01)

                    if interval < 0:
                        break
            except Exception as e:
                self._handle_error(f'Tasklet error: {func.__name__}(): {e}')
                
        func._slowpy_task = True
        self._main_task_coros.append(go_loop())

                
    def _add_schedule_callback(self, func, schedule:str, use_utc:bool):
        """
        Args:
          func: callback function
          schedule: comma-separated HH:MM list. HH or MM can be a *.
        """                    
        time_set: set[int] = set() # int for HHMM
        for hhmm in schedule.split(','):
            hh,mm = hhmm.strip().split(':', 2)
            if hh == '*':
                hh = range(0, 24)
            else:
                try:
                    hh = [int(hh)]
                except Exception:
                    raise Exception(f'Tasklet: bad schedule time: "{hhmm}"')
            if mm == '*':
                mm = range(0, 60)
            else:
                try:
                    mm = [int(mm)]
                except Exception:
                    raise Exception(f'Tasklet: bad schedule time: "{hhmm}"')
            for h in hh:
                for m in mm:
                    time_set.add(100*h+m)

        if len(time_set) == 0:
            return
                    
        time_list:list[int] = sorted(time_set)

        name = func.__name__
        times = [ f"{int(t/100):02d}:{int(t)%100:02d}" for t in time_list ]
        logging.info(f'Tasklet: scheduled {name}() at {",".join(times)}')

        def now():
            if use_utc:
                t = datetime.now(timezone.utc)
            else:
                t = datetime.now()
            return 100 * t.hour + t.minute

        async def go_schedule():
            t = now()
            next_k = 0
            while next_k < len(time_list) and time_list[next_k] <= t:
                next_k += 1
            if next_k == len(time_list):
                next_k = 0
            next_t = time_list[next_k]
            
            try:
                while not ctrl.is_stop_requested():
                    t = now()
                    if t != next_t:
                        await ctrl.aio_sleep(1)
                        continue

                    next_k += 1
                    if next_k == len(time_list):
                        next_k = 0
                    next_t = time_list[next_k]
                
                    result = func()
                    if asyncio.iscoroutine(result):
                        await result

                    if len(time_list) == 1: # once a day -> same HH:MM time
                        await ctrl.aio_sleep(100) # make sure the next check is on a different HH:MM

            except Exception as e:
                self._handle_error(f'Tasklet error: {func.__name__}(): {e}')
                
        func._slowpy_task = True
        self._main_task_coros.append(go_schedule())

                
    def _handle_error(self, message):
        logging.error(message)
        #if sys.exc_info()[0] is not None:
        try:
            tb = traceback.format_exc()
            if tb is not None and len(tb.strip()) > 0:
                logging.warning(tb)
        except:
            pass
    
