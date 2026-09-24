# Created by Sanshiro Enomoto on 17 May 2024 #


import sys, os, time, asyncio, logging
from .node import ControlNode, ControlException, ControlThreadMixin, ControlAsyncTaskMixin


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
    

    def readonly(self):
        """make the node read only (useful when the node is exported)
        """
        return ControlReadOnlyNode(self)

    
    def writeonly(self):
        """make the node write only (useful when the node is exported)
        """
        return ControlWriteOnlyNode(self)

        
    
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
