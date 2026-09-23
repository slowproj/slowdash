# Created by Sanshiro Enomoto on 17 May 2024 #


import sys, os, time, asyncio, inspect, threading, importlib.util, traceback, logging


lock_importing = threading.RLock()


class dualmethod:
    '''decorator for hybrid of object-method(self) and class-method(cls)
    '''
    def __init__(self, func):
        self._func = func

    def __get__(self, instance, owner):
        def wrapper(*args, **kwargs):
            if instance is not None:
                return self._func(instance, *args, **kwargs)
            else:
                return self._func(owner, *args, **kwargs)
        return wrapper


    
class ControlException(Exception):
    def __init__(self, message):
        self._message = message

        
    def __str__(self):
        return str(self._message)


    
class ControlNode:
    def __init__(self):
        # note __init__() might not be called by user subclasses
        self._is_thread_safe = False

        
    # override this
    def set(self, value):
        raise ControlException(f'{type(self).__name__}.set() method not available')

    
    # override this (async version)
    async def aio_set(self, value):
        if getattr(self, '_is_thread_safe', False):
            return await asyncio.to_thread(self.set, value)
        else:
            return self.set(value)   # this may cause a starvation if multiple aio set()/get() tasks are mutual

    
    # override this
    def get(self):
        raise ControlException(f'{type(self).__name__}.set() method not available')


    # override this (async version)
    async def aio_get(self):
        if getattr(self, '_is_thread_safe', False):
            return await asyncio.to_thread(self.get)
        else:
            return self.get()   # this may cause a starvation if multiple aio set()/get() tasks are mutual


    # override this
    def has_data(self):
        raise ControlException(f'{type(self).__name__}.has_data() method not available')

    
    # override this (async version)
    async def aio_has_data(self):
        return self.has_data()   # this assumes has_data() returns immediately

    
    # to be used in subclasses
    @dualmethod
    def sleep(self, duration_sec):
        """stoppable-sleep
        Returns:
            False if stop-request is received, unless True
        """
        # As a stop request can be sent to a specific node, this method must be implemented here
        
        sec10 = int(10*duration_sec)
        subsec10 = 10*duration_sec - sec10
        if sec10 > 0:
            for i in range(sec10):
                if self.is_stop_requested():
                    return False
                else:
                    time.sleep(0.1)
        if subsec10 > 0:
            time.sleep(subsec10/10.0)

        return not self.is_stop_requested()

    
    # to be used in subclasses (async version)
    @dualmethod
    async def aio_sleep(self, duration_sec):
        """stoppable-sleep, async version
        Returns:
            False if stop-request is received, unless True
        """
        # As a stop request can be sent to a specific node, this method must be implemented here
        
        sec10 = int(10*duration_sec)
        subsec10 = 10*duration_sec - sec10
        if sec10 > 0:
            for i in range(sec10):
                if self.is_stop_requested():
                    return False
                else:
                    try:
                        await asyncio.sleep(0.1)
                    except asyncio.CancelledError:
                        return False
                    except:
                        pass
        if subsec10 > 0:
            await asyncio.sleep(subsec10/10.0)

        return not self.is_stop_requested()

    
    # to be used in subclasses
    def wait(self, condition_lambda=None, poll_interval=0.1, timeout=0):
        """stoppable-wait: to be used in subclasses
        Args:
            condition_lambda (lambda x): a function that takes a value from self.get() and returns True or False.
        Returns:
            True if condition is satisfied, None for timeout, False for stop-request
        Examples:
          node.wait(lambda x: (float(x)>100))
        """

        start = time.monotonic()
        while True:
            if self.has_data() is not False:
                if condition_lambda is None:
                    return True
                elif condition_lambda(self.get()):
                    return True
            if self.is_stop_requested():
                return False
            if timeout > 0 and (time.monotonic() - start > timeout):
                break
            time.sleep(poll_interval)
            
        return None
        
            
    # to be used in subclasses (async version)
    async def aio_wait(self, condition_lambda=None, poll_interval=0.1, timeout=0):
        """stoppable-wait: to be used in subclasses, async version
        Args:
            condition_lambda (lambda x): a function that takes a value from self.get() and returns True or False.
        Returns:
            True if condition is satisfied, None for timeout, False for stop-request
        Examples:
          await node.wait(lambda x: (float(x)>100))
        """
        
        start = time.monotonic()
        while True:
            if await self.aio_has_data() is not False:
                if condition_lambda is None:
                    return True
                elif condition_lambda(await self.aio_get()):
                    return True
            if self.is_stop_requested():
                return False
            if timeout > 0 and (time.monotonic() - start > timeout):
                break
            await asyncio.sleep(poll_interval)
            
        return None
        
            
    def snapshot(self):
        """hold the data from get()/aio_get() and provide the same data to children's get()/aio_get()
        Usage:
          | snapshot = device.snapshot().get()
          | value1 = snapshot.child1().get()
          | value2 = snapshot.child2().get()
        Except for get()/aio_get(), the "snapshot" would look exactly like the parent ("device" here)
        """
        return DataSnapshotNode(self)

    
    def readonly(self):
        """make the node read only (useful when the node is exported)
        """
        return ControlReadOnlyNode(self)

    
    def writeonly(self):
        """make the node write only (useful when the node is exported)
        """
        return ControlWriteOnlyNode(self)

        
    # override this to add a child endoint
    @classmethod
    def _node_creator_method(MyClass):    # return a method to be injected
        def child(self, *args, **kwargs):  # "self" here is a parent (the node to which this method is added)
            return MyNodeClassExample(parent=self, *args, **kwargs)
        return child

    
    @classmethod
    def add_node(cls, NodeClass, name=None):
        if not hasattr(NodeClass, '_node_creator_method'):
            raise ControlException('NodeClass does not have _node_creator_method: %s' % str(NodeClass))
        method = NodeClass._node_creator_method()
        if method is None:
            raise ControlException('_node_creator_method() returned None: class %s' % str(NodeClass))
        
        if name is None:
            name = method.__name__

        if not hasattr(cls, name):
            setattr(cls, name, method)
            logging.debug(f'SlowPy Control: imported control node {name}.{cls.__name__}')

            
    @dualmethod
    def import_control_module(this, module_name, search_dirs=[]):
        def _load_module(module_name, search_dirs):
            filename = 'control_%s.py' % module_name
            this_search_dirs = search_dirs + [
                os.path.abspath(os.getcwd()),
                os.path.abspath(os.path.dirname(__file__))
            ]
            for module_dir in this_search_dirs:
                filepath = os.path.join(module_dir, filename)
                if os.path.isfile(filepath):
                    break
            else:
                raise ControlException('unable to find control plugin: %s' % module_name)
        
            try:
                spec = importlib.util.spec_from_file_location(module_name, filepath)
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                error_msg = 'unknown error'
            except Exception as e:
                module = None
                error_msg = str(e)
                logging.error(traceback.format_exc())
                print(traceback.format_exc())

            if module is None:
                if module_name in sys.modules:
                    del sys.modules[module_name]
                raise ControlException('unable to load control module: %s: %s' % (module_name, error_msg))

            dirname = os.path.sep.join(module_dir.split(os.path.sep)[-2:])
            logging.info(f"SlowPy Control: loaded control module {module_name} (@{dirname})")
            
            return module

        
        with lock_importing:
            module = sys.modules.get(module_name, None)
            if module is None:
                module = _load_module(module_name, search_dirs)
                
            node_classes = []
            for class_name, NodeClass in module.__dict__.items():
                if not inspect.isclass(NodeClass):
                    continue
                for member_name, member in inspect.getmembers(NodeClass):
                    if inspect.ismethod(member) and member.__qualname__ == f'{class_name}._node_creator_method':
                        node_classes.append(NodeClass)
            if len(node_classes) == 0:
                raise ControlException('unable to identify Node class: %s' % module_name)
        
            for NodeClass in node_classes:
                this.add_node(NodeClass)
                
        return this

        
    _system_stop_event = threading.Event()
    def is_stop_requested(self):
        if self._system_stop_event.is_set():
            return True
        if hasattr(self, '_node_thread_stop_event') and self._node_thread_stop_event.is_set():
            return True
        return False


    class FieldAccessNode:
        """Helper Node class to set a property value
        This is to be used in child classes, like:
            | class MyNode:
            |     def __init__(self, ...):
            |         self._my_property = foo
            | ....
            | def my_property(self):
            |     self.FieldAccessNode(self, '_my_property')
        """
        def __init__(self, parent_node, field:str):
            self._parent_node = parent_node
            self._field = field

        def set(self, value):
            setattr(self._parent_node, self._field, value)
    
        def get(self):
            return getattr(self._parent_node, self._field)
    
        async def aio_set(self, value):
            setattr(self._parent_node, self._field, value)

        async def aio_get(self):
            return getattr(self._parent_node, self._field)
    
    
    
class DataSnapshotNode:
    """Take one readout data snapshot and propagate it through a node chain.
    Child nodes are expected to keep their parent node and obtain their input though parent.get()/aio_get().
    Methods creating child nodes are rebound to the captured node, so all descendants see the same held readout
    instead of reading the physical device again.
    """
    class _DataCapture(ControlNode):
        def __init__(self, source_node, data):
            self._source_node = source_node
            self._data = data

        def get(self):
            return self._data
        
        async def aio_get(self):
            return self._data
        
        def __getattr__(self, name):
            attr = getattr(self._source_node, name)
            if inspect.ismethod(attr) and attr.__self__ is self._source_node:
                return attr.__func__.__get__(self, type(self))

            return attr
            
    def __init__(self, parent_node):
        self._parent_node = parent_node


    def get(self):
        return self._DataCapture(self._parent_node, self._parent_node.get())
        
                 
    async def aio_get(self):
        return self._DataCapture(self._parent_node, await self._parent_node.aio_get())

    
    def __getattr__(self, name):
        return getattr(self._parent_node, name)



class ControlThreadMixin:
    def start(self):
        """if "self" has the "run()" method, this function will create a thread and call it
        """
        if not hasattr(self, '_node_thread'):
            self._node_thread = None
            self._node_thread_stop_event = threading.Event()
            
        if self._node_thread is not None:
            return self._node_thread
        
        if not callable(getattr(self, 'run', None)):
            raise ControlException('ControlThreadNode.start(): no threading method defined')

        node = self
        class NodeThread(threading.Thread):
            def run(self):
                try:
                    if callable(getattr(node, 'run', None)):
                        node.run()
                finally:
                    node._node_thread = None
    
        self._node_thread_stop_event.clear()
        self._node_thread = NodeThread()
        self._node_thread.daemon = True
        self._node_thread.start()

        return self._node_thread
            

    def stop(self):
        thread = getattr(self, '_node_thread', None)
        if thread is None:
            return
        
        self._node_thread_stop_event.set()
        if threading.current_thread() is not thread:
            thread.join()
        
        
        
class ControlAsyncTaskMixin:
    def start(self):
        """if "self" has the "async aio_run()" method, this function will create a task and start it
        """
        if not hasattr(self, '_node_task'):
            self._node_task = None
        if self._node_task is not None:
            return self._node_task
                
        if not callable(getattr(self, 'aio_run', None)):
            raise ControlException('ControlAsyncTaskNode.start(): no task method defined')

        def on_done(task):
            try:
                task.result()
            except asyncio.CancelledError:
                pass
            except Exception as e:
                task.get_loop().call_exception_handler({
                    'message': 'ControlAsyncTaskMixin task failed',
                    'exception': e,
                    'task': task
                })
            finally:
                self._node_task = None

        self._node_task = asyncio.create_task(self.aio_run())
        self._node_task.add_done_callback(on_done)

        return self._node_task
        
        
    def stop(self):
        task = getattr(self, '_node_task', None)
        if task is not None:
            # the task is actually stopped on the next await
            task.cancel()
        

            
class ControlVariableNode(ControlNode):
    def __init__(self):
        super().__init__()    

        
    ### child nodes ###
    def setpoint(self, limits=(None, None)):
        """hold the setpoint from set()/aio_set() and return the held value on get()/aio_get()
        """
        try:
            self._node_setpoint._limits = limits
        except:
            self._node_setpoint = SetpointNode(self, limits)
        return self._node_setpoint

    
    def ramping(self, change_per_sec:float|None=None, *, set_format:str=None):
        """child node that ramps the set value
        """
        try:
            self._node_async_ramping.stop()
            logging.error('Non-async ramping used while async ramping is running')
            # BUG: the task will not be stopped until next await, which might not happen. Thus the message is an error.
        except:
            pass
        
        try:
            self._node_ramping
            if change_per_sec is not None:
                self._node_ramping._change_per_sec = change_per_sec
        except:
            self._node_ramping = RampingThreadNode(self, change_per_sec, set_format=set_format)
            
        return self._node_ramping
    

    def async_ramping(self, change_per_sec:float|None=None, *, set_format:str=None):
        """child node that ramps the set value
        """
        try:
            self._node_ramping.stop()
            logging.warning('Async ramping used while non-async ramping is running: stopped')
        except:
            pass
        
        try:
            self._node_async_ramping
            if change_per_sec is not None:
                self._node_async_ramping._change_per_sec = change_per_sec
        except:
            self._node_async_ramping = RampingTaskNode(self, change_per_sec, set_format=set_format)
            
        return self._node_async_ramping
    

    def oneshot(self, duration=None, normal=None):
        """child node that sets a value for a given duration and restores the original value
        """
        
        try:
            self._node_oneshot
        except:
            self._node_oneshot = OneshotNode(self, duration, normal)
        return self._node_oneshot
    

    
class SetpointNode(ControlNode):
    def __init__(self, node, limits=(None, None)):
        super().__init__()
        self._is_thread_safe = getattr(node, '_is_thread_safe', False)
            
        self._node = node
        self._setpoint = None
        self._limits = limits

        
    def _check_limits(self, value):
        if self._limits[0] is not None or self._limits[1] is not None:
            try:
                x = float(value)
            except:
                raise ControlException('numeric value is expected for setpoint limits')
            
            if self._limits[0] is not None and x < float(self._limits[0]):
                logging.error(f'setpoint lower than the lower limit: {x} < {self._limits[0]}')
                return False
            if self._limits[1] is not None and x > float(self._limits[1]):
                logging.error(f'setpoint greater than the upper limit: {x} > {self._limits[1]}')
                return False

        return True

            
    def set(self, value):
        if self._check_limits(value):
            self._setpoint = value
            self._node.set(value)

        
    async def aio_set(self, value):
        if self._check_limits(value):
            self._setpoint = value
            await self._node.aio_set(value)

    
    def get(self):
        return self._setpoint


    async def aio_get(self):
        return self.get()
    
    
    # child node which is the parent
    def current(self):
        return self._node
    
    
        
class RampingBaseNode(ControlNode):
    def __init__(self, value_node, change_per_sec:float|None, *, set_format=None):
        super().__init__()
        self._is_thread_safe = getattr(value_node, '_is_thread_safe', False)
        
        self._value_node = value_node
        if change_per_sec is None:
            self._change_per_sec = None
        else:
            try:
                self._change_per_sec = abs(float(change_per_sec))
            except:
                self._change_per_sec = None

        self._set_format = set_format
        
        self._target_value = None
        self._running = False

        
    def set(self, target_value:float|None):
        if target_value is None:
            self._target_value = None
            self._running = False
            return
        
        try:
            self._target_value = float(target_value)
            self._running = True
        except:
            raise ControlException('numeric value is expected')
        if self._change_per_sec is None or not (self._change_per_sec > 0):
            raise ControlException('invalid ramping speed')
        
        
    async def aio_set(self, target_value:float|None):
        return self.set(target_value)
            

    def get(self):
        return self._target_value


    async def aio_get(self):
        return self._target_value


    # child nodes
    def status(self):
        return RampingStatusNode(self)
        

            
class RampingThreadNode(ControlThreadMixin, RampingBaseNode):
    def __init__(self, value_node, change_per_sec:float|None, *, set_format=None):
        super().__init__(value_node, change_per_sec, set_format=set_format)
        self.start()

        
    def run(self):
        if not self._is_thread_safe:
            logging.error('RampingThreadNode used for non thread-safe node')

        while True:
            if self.is_stop_requested() or self._node_thread_stop_event.is_set():
                break
            if not self._running or self._target_value is None:
                time.sleep(0.1)
                continue
            
            try:
                current_value = float(self._value_node.get())
            except Exception as e:
                logging.warning(f'ramping: unable to get the current value: {e}')
                self._running = False
                continue
        
            diff = current_value - self._target_value
            if abs(diff) <= self._change_per_sec:
                current_value = self._target_value
                self._running = False
            elif diff > 0:
                current_value -= self._change_per_sec
            else:
                current_value += self._change_per_sec

            if self._set_format is not None:
                set_value = self._set_format.format(current_value)
            else:
                set_value = current_value

            try:
                self._value_node.set(set_value)
            except Exception as e:
                logging.warning(f'ramping: unable to set a ramping value: {e}')
                self._running = False
                
            for i in range(10):
                if self.is_stop_requested():
                    self._running = False
                    break
                else:
                    time.sleep(0.1)
                               

            
class RampingTaskNode(ControlAsyncTaskMixin, RampingBaseNode):
    def __init__(self, value_node, change_per_sec:float|None, *, set_format=None):
        super().__init__(value_node, change_per_sec, set_format=set_format)
        self.start()

        
    async def aio_run(self):
        while True:
            if self.is_stop_requested():
                break
            if not self._running or self._target_value is None:
                await asyncio.sleep(0.1)
                continue
            
            try:
                current_value = float(await self._value_node.aio_get())
            except Exception as e:
                logging.warning(f'ramping: unable to get the current value: {e}')
                self._running = False
                continue
        
            diff = current_value - self._target_value
            if abs(diff) <= self._change_per_sec:
                current_value = self._target_value
                self._running = False
            elif diff > 0:
                current_value -= self._change_per_sec
            else:
                current_value += self._change_per_sec

            if self._set_format is not None:
                set_value = self._set_format.format(current_value)
            else:
                set_value = current_value

            try:
                await self._value_node.aio_set(set_value)
            except Exception as e:
                logging.warning(f'ramping: unable to set a ramping value: {e}')
                self._running = False
                
            for i in range(10):
                if self.is_stop_requested():
                    self._running = False
                    break
                else:
                    await asyncio.sleep(0.1)

                    
    
class RampingStatusNode(ControlNode):
    def __init__(self, ramping_node):
        super().__init__()
        self._is_thread_safe = getattr(ramping_node, '_is_thread_safe', False)

        self._ramping_node = ramping_node

        
    def set(self, zero_to_stop):
        """set(0) to stop ramping
        """
        if str(zero_to_stop) == '0' or bool(zero_to_stop) == False:
            self._ramping_node._running = False

    
    def get(self):
        """returns True if ramping is in progress
        """
        return self._ramping_node._running


    async def aio_set(self, zero_to_stop):
        return self.set(zero_to_stop)


    async def aio_get(self):
        return self.get()



class ControlReadOnlyNode(ControlNode):
    def __init__(self, node):
        super().__init__()
        self._is_thread_safe = getattr(node, '_is_thread_safe', False)
        
        self._node = node

    def set(self, value):
        raise ControlException('node is read-only')

    def get(self):
        return self._node.get()

    async def aio_set(self, value):
        raise ControlException('node is read-only')

    async def aio_get(self):
        return await self._node.aio_get()

    
    
class ControlWriteOnlyNode(ControlNode):
    def __init__(self, node):
        super().__init__()
        self._is_thread_safe = getattr(node, '_is_thread_safe', False)
        
        self._node = node


    def set(self, value):
        return self._node.set(value)

    def get(self):
        raise ControlException('node is write-only')

    async def aio_set(self, value):
        return await self._node.aio_set(value)

    async def aio_get(self):
        raise ControlException('node is write-only')


    
class OneshotNode(ControlNode):
    def __init__(self, node, duration=None, normal=None):
        """A value by `set()` is held for a given duration, then goes back to the `normal` value
        Args:
            duration (float or None): if None, the first get() after set() returns the set-value
        """
        super().__init__()
        self._is_thread_safe = getattr(node, '_is_thread_safe', False)
        
        self._node = node
        self._duration = abs(float(duration)) if duration is not None else None
        self._normal = normal
        
        self._start_time = None

        
    def set(self, value):
        if self._normal is None:
            self._normal = self._node.get()
        self._node.set(value)
        self._start_time = time.monotonic()

        
    async def aio_set(self, value):
        if self._normal is None:
            self._normal = await self._node.aio_get()
        await self._node.aio_set(value)
        self._start_time = time.monotonic()

        
    def get(self):
        if self._start_time is not None:
            if self._duration is None:
                value = self._node.get()
                self._node.set(self._normal)
                self._start_time = None
                return value
                
            if time.monotonic() > self._start_time + self._duration:
                self._node.set(self._normal)
                self._start_time = None
                
        return self._node.get()


    async def aio_get(self):
        if self._start_time is not None:
            if self._duration is None:
                value = await self._node.aio_get()
                await self._node.aio_set(self._normal)
                self._start_time = None
                return value
                
            if time.monotonic() > self._start_time + self._duration:
                await self._node.aio_set(self._normal)
                self._start_time = None
                
        return await self._node.aio_get()
