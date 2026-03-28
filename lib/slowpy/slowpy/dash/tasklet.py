# Created by Sanshiro Enomoto on 13 August 2025 #

import sys, time, asyncio, threading, inspect, traceback, logging
from datetime import datetime, timezone
from slowpy.control import control_system as ctrl
from .mesh import Mesh

logging.basicConfig(level=logging.DEBUG)


class Tasklet:
    def __init__(self):
        self.app = None
        self.module = None
        self.mesh = Mesh()
        self.task_coros = []
        self.task_tasks = set()

        self.initialize_completed = False


    def run(self, params:dict|None=None, mesh_url:str|None=None):
        caller_frame = inspect.currentframe().f_back
        modname = caller_frame.f_globals.get('__name__')
        self.module = sys.modules.get(modname)
        if self.module is None:
            logging.error(f'Tasklet: unable to get module: {modname}')
            return
        logging.debug(f'Tasklet took over module {self.module.__name__}')

        self.mesh.connect(mesh_url)
        
        ctrl.stop_by_signal()
        
        try:
            asyncio.run(self._start(params or {}))
        except asyncio.CancelledError:
            pass
            

    async def _start(self, params):
        try:
            await self.mesh.aio_start()
            
            self.task_tasks = set()
            for coro in self.task_coros:
                task = asyncio.create_task(coro)
                task.add_done_callback(self.task_tasks.discard)
                self.task_tasks.add(task)
                
            await self._start_script(params)
            
        except Exception as e:
            raise e
        finally:
            await self.mesh.aio_close()
            for task in self.task_tasks:
                task.cancel()
            try:
                await task
            except Exception as e:
                logging.error(f'Error in Tasklet Callback: {e}')
            except:
                pass
                
        
    async def _start_script(self, params):
        func_setup = self._get_func('_setup')
        func_initialize = self._get_func('_initialize')
        func_run = self._get_func('_run')
        func_loop = self._get_func('_loop')
        func_finalize = self._get_func('_finalize')
        
        if func_setup:
            nargs = len(inspect.signature(func_setup).parameters)
            if nargs >= 2:
                args = [ self.app, params ]
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
                self._handle_error('Tasklet error: _setup(): %s' % str(e))

        if func_initialize:
            nargs = len(inspect.signature(func_initialize).parameters)
            if nargs >= 1:
                args = [ params ]
            else:
                args = []
            try:
                if inspect.iscoroutinefunction(func_initialize):
                    await func_initialize(*args)
                else:
                    func_initialize(*args)
            except Exception as e:
                self._handle_error(f'Tasklet error: _initialize(): {e}')
            
        self.initialize_completed = True
        
        if func_run and not ctrl.is_stop_requested():
            try:
                if inspect.iscoroutinefunction(func_run):
                    await func_run()
                else:
                    func_run()
            except Exception as e:
                self._handle_error(f'Tasklet error: _run(): {e}')
                
        while not ctrl.is_stop_requested():
            if func_loop:
                try:
                    if inspect.iscoroutinefunction(func_loop):
                        await func_loop()
                    else:
                        func_loop()
                except Exception as e:
                    self._handle_error(f'Tasklet error: _loop(): {e}')
                    func_loop = False
                await asyncio.sleep(0.01)
            else:
                # not to proceed to finalize() before a stop_event occurs
                await asyncio.sleep(0.1)
                
        if func_finalize:
            try:
                if inspect.iscoroutinefunction(func_finalize):
                    await func_finalize()
                else:
                    func_finalize()
            except Exception as e:
                self._handle_error(f'Tasklet error: _finalize(): {e}')


    def _get_func(self, name):
        if self.module is None:
            return None
        if (name in self.module.__dict__) and callable(self.module.__dict__[name]):
            logging.debug(f'Tasklet callback {name} found')
            return self.module.__dict__[name]
        else:
            logging.debug(f'Tasklet callback {name} not defined')
            return None

        
    def add_once_callback(self, func, delay:float):
        """
        Args:
          func: callback function
          delay: func execution delay after completion of intialization
        """
        async def go_once():
            try:
                start = time.monotonic()
                while not ctrl.is_stop_requested():
                    if not self.initialize_completed:
                        await asyncio.sleep(0.1)
                        continue

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
                logging.error(f'Error in Tasklet once function: {e}')
                
        self.task_coros.append(go_once())

                
    def add_loop_callback(self, func, interval:float):
        """
        Args:
          func: callback function
          interval: func execution intervals. Zero for no wait, negative to run the func only once.
        """
        async def go_loop():
            try:
                last_execusion_time = time.monotonic()
                while not ctrl.is_stop_requested():
                    if not self.initialize_completed:
                        await asyncio.sleep(0.1)
                        continue
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
                logging.error(f'Error in Tasklet loop function: {e}')
                
        self.task_coros.append(go_loop())

                
    def add_schedule_callback(self, func, schedule:str, use_utc:bool):
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
                logging.error(f'Error in Tasklet loop function: {e}')
                
        self.task_coros.append(go_schedule())

                
    def _handle_error(self, message):
        logging.error(message)
        #if sys.exc_info()[0] is not None:
        try:
            tb = traceback.format_exc()
            if tb is not None and len(tb.strip()) > 0:
                logging.warning(tb)
        except:
            pass


    def is_stop_requested(self):
        return ctrl.is_stop_requested()
    
        
    def publish(self, topic:str, value):
        loop = asyncio.get_running_loop()
        loop.create_task(self.aio_publish(topic, value))
    
        
    async def aio_publish(self, topic:str, value):
        return await self.mesh.aio_publish(topic, value)
    
        
    def once(self, delay:float=0):
        """decorator to add a tasklet task
        """
        def wrapper(func):
            self.add_once_callback(func, delay)
            return func
        return wrapper
        

    def loop(self, interval:float=0):
        """decorator to add a tasklet task
        """
        def wrapper(func):
            self.add_loop_callback(func, interval)
            return func
        return wrapper
        

    def schedule(self, time_list:str, *, use_utc:bool=False):
        """decorator to add a tasklet task
        Args:
        time_list: comma-separated list of times in HH:MM. HH and MM must be an integer or *.
        use_utc: set True to use the UTC time.
        """
        def wrapper(func):
            self.add_schedule_callback(func, time_list, use_utc)
            return func
        return wrapper
        

    def on(self, topic:str):
        """decorator to make a message handler
        Args:
        - topic: path pattern to match
        """
        return self.mesh.on(topic)

