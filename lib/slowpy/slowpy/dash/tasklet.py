# Created by Sanshiro Enomoto on 13 August 2025 #

import sys, time, asyncio, threading, inspect, traceback, logging
from slowpy.control import control_system as ctrl
from .mesh import Mesh

#logging.basicConfig(level=logging.DEBUG)


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

        
    def add_loop_callback(self, func, interval:float):
        """
        Args:
          func: callback function
          interval: func execution intervals. Zero for no wait, negative to run the func only once.
        """
        async def go():
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
                
        self.task_coros.append(go())

                
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
    
        
    async def aio_publish(self, topic:str, value):
        return await self.mesh.aio_publish(topic, value)
    
        
    def loop(self, interval=0):
        """decorator to add a tasklet task
        """
        def wrapper(func):
            self.add_loop_callback(func, interval)
            return func
        return wrapper
        

    def on(self, topic:str):
        """decorator to make a message handler
        Args:
        - topic: path pattern to match
        """
        return self.mesh.on(topic)

