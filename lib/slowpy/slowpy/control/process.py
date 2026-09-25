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

    
    def ramping(self, change_per_sec:float|None=None, *, set_format:str=''):
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
    

    def async_ramping(self, change_per_sec:float|None=None, *, set_format:str=''):
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
    

    def pid(self, sensing_node, Kp:float, Ki:float, Kd:float, *, interval:float=1.0, output_limits:tuple[float|None,float|None]=(None, None), set_format:str=''):
        """PID-control this node using values read from sensing_node.
        Usage:
            control_device.pid(sensor, Kp, Ki, Kd).set(target)
        set(None) stops control. Positive gains assume that increasing the control output increases the sensed value.
        """
        if hasattr(self, '_node_pid'):
            self._node_pid.do_configure(
                Kp=Kp, Ki=Ki, Kd=Kd,
                interval=interval, output_limits=output_limits,
                set_format=set_format,
                sensing_node=sensing_node,
            )
        else:
            self._node_pid = PIDThreadNode(
                self, sensing_node, Kp, Ki, Kd,
                interval=interval, output_limits=output_limits,
                set_format=set_format
            )
        return self._node_pid


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
    def __init__(self, value_node, change_per_sec:float|None, *, set_format:str=''):
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
    def __init__(self, value_node, change_per_sec:float|None, *, set_format:str=''):
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

            if len(self._set_format) > 0:
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
    def __init__(self, value_node, change_per_sec:float|None, *, set_format:str=''):
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

            if len(self._set_format) > 0:
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
        return {
            'running': self._ramping_node._running,
        }


    async def aio_set(self, zero_to_stop):
        return self.set(zero_to_stop)


    async def aio_get(self):
        return self.get()



class PIDThreadNode(ControlThreadMixin, ControlNode):
    """PID controller node running in a background thread
    - The parent/control node is the actuator output and sensing_node is the process-variable input.
    - set(target) starts/updates regulation and set(None) stops it.
    - for the D component, -dy/dt is used instead of de/dt, to prevent steps of setpoint from going into the D term
    """

    def __init__(self,
        control_node, sensing_node,
        Kp:float, Ki:float, Kd:float,
        *,
        interval:float=1.0,
        output_limits:tuple[float|None,float|None]=(None, None),
        set_format:str=''
    ):
        super().__init__()
        self._control_node = control_node
        self._target_value = None
        self._running = False
        
        self.do_configure(
            Kp=Kp, Ki=Ki, Kd=Kd,
            interval=interval, output_limits=output_limits,
            set_format=set_format,
            sensing_node=sensing_node
        )

        self._time = None
        self._measurement = None
        self._deviation = 0.0
        self._integral = 0.0
        self._derivative = 0.0
        self._output = None
        self._saturated_low = False
        self._saturated_high = False

        self.start()


    def run(self):
        if not self._is_thread_safe:
            logging.error('PIDNode used with non thread-safe control or sensing node')

        while True:
            # check if the PID loop is running
            if self.is_stop_requested() or self._node_thread_stop_event.is_set():
                break
            if not self._running or self._target_value is None:
                time.sleep(0.1)
                continue
            cycle_start = time.monotonic()

            # new measurement
            try:
                new_measurement = float(self._sensing_node.get())
            except Exception as e:
                logging.warning(f'PID: unable to get sensing value: {e}')
                self.sleep(self._interval)
                continue

            # PID update
            now = time.monotonic()
            self._deviation = self._target_value - new_measurement
            if self._time is None:
                dt = 0.0
                self._derivative = 0.0
                if self._Ki != 0:
                    # bumpless transfer if the system is already near the target (switching from manual to auto etc.)
                    try:
                        output = float(self._control_node.get())
                        self._integral = (output - self._Kp * self._deviation) / self._Ki
                    except Exception as e:
                        self._integral = 0
                        logging.warning(f'PID: bumpless transfer failed: {e}')
            else:
                dt = now - self._time
                if dt > 0:
                    # not derivative as deviation/dt, to prevent steps of setpoint from going into the D term (derivative kick)
                    self._derivative = -(new_measurement - self._measurement) / dt
                else:
                    self._derivative = 0
            this_integral = self._integral + self._deviation * dt
            self._time = now
            self._measurement = new_measurement
            
            self._output = self._Kp * self._deviation + self._Ki * this_integral + self._Kd * self._derivative

            # output limits
            low, high = self._output_limits
            self._saturated_low = low is not None and self._output < low
            self._saturated_high = high is not None and self._output > high
            if self._saturated_low:
                self._output = low
            elif self._saturated_high:
                self._output = high

            # anti-windup update on the integration
            integral_drive = self._Ki * self._deviation
            if not ((self._saturated_high and integral_drive > 0) or (self._saturated_low and integral_drive < 0)):
                self._integral = this_integral

            # new control output
            if len(self._set_format) > 0:
                set_value = self._set_format.format(self._output)
            else:
                set_value = self._output
            try:
                self._control_node.set(set_value)
            except Exception as e:
                logging.warning(f'PID: unable to set control value: {e}')
                self._running = False
                continue

            # sleep until the next cycle
            remaining = self._interval - (time.monotonic() - cycle_start)
            if remaining > 0:
                self.sleep(remaining)


    def do_configure(self, *,
        Kp:float|None=None, Ki:float|None=None, Kd:float|None=None,
        interval:float|None=None,
        output_limits:tuple[float|None,float|None]|None=None,
        set_format:str|None=None,
        sensing_node = None,
    ):
        try:
            self._Kp = float(Kp) if Kp is not None else self._Kp
            self._Ki = float(Ki) if Ki is not None else self._Ki
            self._Kd = float(Kd) if Kd is not None else self._Kd
            self._interval = float(interval) if interval is not None else self._interval
        except:
            raise ControlException('PID: floating number is expected')
        if self._interval <= 0:
            raise ControlException('PID: interval must be positive')

        if output_limits is not None:
            try:
                low, high = output_limits
                low = None if low is None else float(low)
                high = None if high is None else float(high)
            except Exception:
                raise ControlException('PID: output_limits must be (low:float, high:float)')
            if low is not None and high is not None and low > high:
                raise ControlException(f'PID: invalid output_limits: low({low}) > high({high})')
            self._output_limits = (low, high)

        if set_format is not None:
            self._set_format = set_format
            
        if sensing_node is not None:
            self._sensing_node = sensing_node
            self._is_thread_safe = (
                getattr(self._control_node, '_is_thread_safe', False) and
                getattr(self._sensing_node, '_is_thread_safe', False)
            )
        
        self.do_reset()

    
    def do_reset(self):
        self._time = None
        self._measurement = None
        self._integral = 0.0
        self._saturated_low = False
        self._saturated_high = False


    def set(self, target_value:float):
        if target_value is None:
            self._target_value = None
            self._running = False
            self.do_reset()
            return

        self._target_value = float(target_value)
        if not self._running:
            self.do_reset()
            
        self._running = True


    async def aio_set(self, target_value):
        return self.set(target_value)


    def get(self):
        return self._target_value


    async def aio_get(self):
        return self.get()


    def status(self):
        return PIDStatusNode(self)


    
class PIDStatusNode(ControlNode):
    def __init__(self, pid_node):
        super().__init__()
        self._is_thread_safe = getattr(pid_node, '_is_thread_safe', False)
        
        self._pid_node = pid_node

        
    def set(self, zero_to_stop):
        if str(zero_to_stop) == '0' or bool(zero_to_stop) == False:
            self._pid_node.set(None)

            
    def get(self):
        return {
            'running': self._pid_node._running,
            'time': self._pid_node._time,
            'setpoint': self._pid_node._target_value,
            'measurement': self._pid_node._measurement,
            'output': self._pid_node._output,
            'saturated_low': self._pid_node._saturated_low,
            'saturated_high': self._pid_node._saturated_high,
            'Kp': self._pid_node._Kp,
            'Ki': self._pid_node._Ki,
            'Kd': self._pid_node._Kd,
            'interval': self._pid_node._interval,
            'limit_low': self._pid_node._output_limits[0],
            'limit_high': self._pid_node._output_limits[1],
        }

    
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
