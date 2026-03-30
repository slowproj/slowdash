# Created by Sanshiro Enomoto on 13 August 2025 #

import sys, time, copy, asyncio, threading, inspect, traceback, logging
from datetime import datetime, timezone
from slowpy.control import control_system as ctrl
from .mesh import Mesh

logging.basicConfig(level=logging.DEBUG)


class Tasklet:
    def __init__(self, name:str|None=None):
        self.name = name
        self.params = {}
        self.mesh_url = None
        
        self.mesh = Mesh()
        self.initialize_task_coros = []
        self.main_task_coros = []
        self.finalize_task_coros = []


    def run(self, params:dict|None=None, mesh_url:str|None=None):
        self.params = copy.deepcopy(params)
        self.mesh_url = mesh_url

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
    
        
    async def aio_publish(self, topic:str, value, *, headers:dict|None=None):
        return await self.mesh.publisher(topic).headers(headers or {}).aio_set(value)

        
    def publish(self, topic:str, value, *, headers:dict|None=None):
        loop = asyncio.get_running_loop()
        loop.create_task(self.aio_publish(topic, value, headers=headers))
    
        
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
        

    def loop(self, interval:float=0):
        """decorator to add a tasklet task
        """
        def wrapper(func):
            self._add_loop_callback(func, interval)
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
        

    def on(self, topic:str):
        """decorator to make a message handler
        Args:
        - topic: path pattern to match
        """
        def wrapper(func):
            self._add_subscription_callback(func, topic)
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
            self._add_once_callback(func_run)
        
        func_loop = _get_func('_loop')
        if func_loop:
            if inspect.iscoroutinefunction(func_loop):
                self._add_loop_callback(func_loop, 0)
            else:
                # use of time.sleep() in user function will cause starving: do not allow it
                logging.error(f'Tasklet: _loop() callback must be async')
        

    async def _start(self):
        self.mesh.connect(self.mesh_url)
        
        try:
            await asyncio.gather(*self.initialize_task_coros)
        except Exception as e:
            raise e
        finally:
            await self.mesh.aio_close()
        
        main_tasks = set()
        try:
            for coro in self.main_task_coros:
                task = asyncio.create_task(coro)
                task.add_done_callback(main_tasks.discard)
                main_tasks.add(task)
            while not ctrl.is_stop_requested():
                await ctrl.aio_sleep(1)
        except Exception as e:
            raise e
        
        finally:
            for task in main_tasks:
                task.cancel()
            try:
                await task
            except Exception as e:
                self._handle_error(f'Tasklet error during clean up: {e}')
            except:
                pass
            
            try:
                await asyncio.gather(*self.finalize_task_coros)
            except Exception as e:
                self._handle_error(f'error during clean up: {e}')
            except:
                pass
            
            await self.mesh.aio_close()

            
    def _add_initialize_callback(self, func):
        """
        Args:
          func: callback function
        """
        async def go_initialize():
            nargs = len(inspect.signature(func).parameters)
            if nargs >= 1:
                args = [ self.params ]
            else:
                args = []
            try:
                result = func(*args)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                self._handle_error(f'Tasklet error: {func.__name__}(): {e}')

        func._slowpy_task = True
        self.initialize_task_coros.append(go_initialize())

                
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
        self.finalize_task_coros.append(go_finalize())

                
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
                
        self.main_task_coros.append(go_once())

                
    def _add_loop_callback(self, func, interval:float):
        """
        Args:
          func: callback function
          interval: func execution intervals. Zero for no wait, negative to run the func only once.
        """
        async def go_loop():
            try:
                last_execusion_time = time.monotonic()
                while not ctrl.is_stop_requested():
                    if interval > 0:
                        now = time.monotonic()
                        lapse = now - last_execusion_time
                        if lapse < interval:
                            await asyncio.sleep(min(interval-lapse, 0.5))
                            continue
                        last_execusion_time += int(lapse / interval) * interval
                    
                    result = func()
                    if asyncio.iscoroutine(result):
                        await result
                    else:
                        await asyncio.sleep(0.01)

                    if interval < 0:
                        break
            except Exception as e:
                self._handle_error(f'Tasklet error: {func.__name__}(): {e}')
                
        func._slowpy_task = True
        self.main_task_coros.append(go_loop())

                
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
        self.main_task_coros.append(go_schedule())

                
    def _add_subscription_callback(self, func, topic:str):
        """
        Args:
          func: callback function
          topic: topic filter
        """
        func._slowpy_task = True

        nargs = len(inspect.signature(func).parameters)
        if nargs > 2:
            logging.error(f'Invalid mesh message handler: wrong number of arguments')
            return None

        async def go_subscription():
            subscriber = self.mesh.subscriber(topic)
            try:
                while not ctrl.is_stop_requested():
                    headers, data = await subscriber.aio_get()
                    if data is None:
                        continue
                    if nargs == 0:
                        result = func()
                    elif nargs == 1:
                        result = func(data)
                    elif nargs == 2:
                        result = func(headers, data)
                    if asyncio.iscoroutine(result):
                        await result
            except Exception as e:
                self._handle_error(f'Tasklet error: {func.__name__}(): {e}')
                
        self.main_task_coros.append(go_subscription())

                
    def _handle_error(self, message):
        logging.error(message)
        #if sys.exc_info()[0] is not None:
        try:
            tb = traceback.format_exc()
            if tb is not None and len(tb.strip()) > 0:
                logging.warning(tb)
        except:
            pass
    
