# Created by Sanshiro Enomoto on 13 August 2025 #

import sys, time, copy, asyncio, inspect, traceback, logging
from datetime import datetime, timezone
from slowpy.control import control_system as ctrl
from .dash import Dash
from .mesh import Mesh


class Tasklet:
    def __init__(self, name:str|None=None):
        self._name = name
        self._params = {}
        
        self._dash_url = None
        self._dash = Dash()
        
        self._mesh_url = None
        self._mesh = Mesh(name=name, on_reconnect=self.on_reconnect, name_prefix_to_drop='slowtask-')
        if self._name is None:
            self._name = self._mesh.name
        
        self._mesh_list = [ self._mesh ]
        self._initialize_task_coros = []
        self._main_task_coros = []
        self._finalize_task_coros = []

        self._heartbeat_interval = 10
        self._next_heartbeat_time = 0

        
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


    def run(self, params:dict|None=None, slowdash_url:str|None=None, mesh_url:str|None=None):
        self._params = copy.deepcopy(params)
        self._dash_url = slowdash_url or self._dash_url
        self._mesh_url = mesh_url or self._mesh_url
        if self._mesh_url is None and self._dash_url is not None:
            if self._dash_url.startswith('http://'):
                self._mesh_url = 'slowmq' + self._dash_url[4:]
            elif self._dash_url.startswith('https://'):
                self._mesh_url = 'slowmqs' + self._dash_url[5:]

        caller_frame = inspect.currentframe().f_back
        modname = caller_frame.f_globals.get('__name__')
        module = sys.modules.get(modname)
        if module is None:
            logging.error(f'Tasklet: unable to get module: {modname}')
        else:
            self._scan_oldstyle_callbacks(module)
            
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
        

    #### Internal Methods ####

    def _scan_oldstyle_callbacks(self, module):
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
        

    async def _start(self):
        if self._dash_url is not None:
            self._dash.connect(self._dash_url)
        if self._mesh_url is not None:
            self._mesh.connect(self._mesh_url)
        
        try:
            await asyncio.gather(*self._initialize_task_coros)
        except Exception as e:
            try:
                for mesh in self._mesh_list:
                    await mesh.aio_close()   
                await self._dash.aio_close()
            except Exception:
                pass
            raise e

        # mesh.aio_publish() is possible even before aio_start()            
        for mesh in self._mesh_list:
            await mesh.aio_start()   

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
                await ctrl.aio_sleep(1)
        except Exception as e:
            raise e
        
        finally:
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

            for mesh in self._mesh_list:
                await mesh.aio_close()
            await self._dash.aio_close()   


    async def on_reconnect(self):
        await self._publish_spec()

        
    async def _publish_spec(self):
        spec_doc = {
            'mesh_id': self.mesh.mesh_id,
            'name': self.name,
            'functions': [ {"name": name} for name,func in self.mesh.export_functions().items() ],
            'variables': [ {"name": name} for name,variable in self.mesh.export_variables().items() ],
        }
        await self.mesh.aio_publish(f'sd.task.spec.{self.name}', spec_doc)
        
        
    async def _heartbeat(self):
        now = time.time()
        if now > self._next_heartbeat_time:
            self._next_heartbeat_time = now + self._heartbeat_interval
            heartbeat_doc = {
                'mesh_id': self.mesh.mesh_id,
                'name': self.name,
                'timestamp': int(now)
            }
            await self.mesh.aio_publish(f'sd.task.heartbeat.{self.name}', {}, headers=heartbeat_doc)

    
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
    
