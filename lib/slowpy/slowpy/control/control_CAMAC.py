# Created by Sanshiro Enomoto on 29 July 2026 #

"""SlowPy/Control CAMAC plugin
- This uses the camdrv2 device driver, available at https://github.com/SanshiroEnomoto/camdrv2
"""

import os, time, errno, logging
import slowpy.control as spc


class CamacNode(spc.ControlNode):
    def __init__(self, crate:int, dummy:bool=False):
        self.crate = crate
        self._dummy = DummyDevice() if dummy else None
        
        self._is_open = False
        self._is_error = False


    def open(self, crate:int|None=None):
        if self._dummy is not None:
            return True

        if self._is_error:
            return False
        
        if not self._is_open:
            self._is_open = True
            
            status = COPEN()
            if status != 0:
                self._is_error = True
                logging.error(f"COPEN(): {os.strerror(status)}")
                return False
            
            if crate is None:
                crate = self.crate
            self.crate = None
                
        if crate is not None and self.crate != crate:
            self.crate = crate
            status = CSETCR(self.crate)
            if status != 0:
                logging.error(f"CSETCR(): {os.strerror(status)}")
        
        return True
        

    def close(self):
        if self._dummy is not None:
            return

        if self._is_open:
            status = CCLOSE()
            if status != 0:
                logging.error(f"CCLOSE(): {os.strerror(status)}")
                
        self._is_open = False
        self._is_error = False

        
    ## child nodes ##
    def module(self, station:int):
        return ModuleNode(self, station)

    
    def module_REPIC_RPC022(self, station:int):
        module = ModuleNode(self, station)
        module.function_read = 0
        module.function_write = None
        module.function_clear = 9
        module.function_enable_lam = None
        module.function_test_lam = None
        module.function_clear_lam = None
        return module

    
    def module_Hoshin_C009(self, station:int):
        module = ModuleNode(self, station)
        module.function_read = 0
        module.function_write = None
        module.function_clear = 9
        module.function_enable_lam = None
        module.function_test_lam = 8
        module.function_clear_lam = 10
        return module

    
    @classmethod
    def _node_creator_method(cls):
        def camac(self, crate:int, dummy:bool=False):
            try:
                self.camac_node
            except:
                self.camac_node = CamacNode(crate=crate, dummy=dummy)
            return self.camac_node

        return camac


    
class ModuleNode(spc.ControlVariableNode):
    def __init__(self, camac_node, station:int):
        self.camac_node = camac_node
        self.station = station
        
        self.function_read = 0
        self.function_write = 16
        self.function_clear = 9
        self.function_enable_lam = 26
        self.function_clear_lam = 10
        
        self._is_lam_enabled = False
        
        
    def clear(self):
        if self.camac_node._dummy is not None:
            return self.camac_node._dummy.clear()
        
        self.camac_node.open()
        
        if self.function_clear is not None:
            n, a, f = self.station, 0, self.function_clear
            q, x, data, _ = CAMAC(n, a, f)
            if x == 0:
                #raise spc.ControlException(f"CAMAC.clear(): CAMAC(): No-X from station {n} (F{f})")
                logging.error(f"CAMAC.clear(): CAMAC(): No-X from station {n} (F{f})")
                self.function_clear = None
        
        if self._is_lam_enabled and self.function_clear_lam is not None:
            n, a, f = self.station, 0, self.function_clear_lam
            q, x, data, _ = CAMAC(n, a, f)
            if x == 0:
                #raise spc.ControlException(f"CAMAC.clear(): CAMAC(): No-X from station {n} (F{f})")
                logging.error(f"CAMAC.clear(): CAMAC(): No-X from station {n} (F{f})")
                self.function_clear_lam = None
        
        
    def wait(self, timeout=0):
        """stoppable-wait
        Returns:
          True if LAM is set, None for timeout, False for stop-request
        """

        if self.camac_node._dummy is not None:
            return self.camac_node._dummy.wait()
        
        self.camac_node.open()
        if not self._is_lam_enabled:
            self._is_lam_enabled = True
            if self.function_enable_lam is not None:
                n, a, f = self.station, 0, self.function_enable_lam
                q, x, data, _ = CAMAC(n, a, f)
                if x == 0:
                    #raise spc.ControlException(f"CAMAC.wait(): CAMAC(): No-X from station {n} (F{f})")
                    logging.error(f"CAMAC.wait(): CAMAC(): No-X from station {n} (F{f})")

        start = time.monotonic()
        lam_mask = 0x01 << (self.station-1)
        while True:
            try:
                result = CWLAM2(timeout=1)
            except OSError as e:
                logging.error(f"CAMAC.wait(): CWLAM2(): {e}")
                
            if result is None: # timeout
                continue
            elif result & lam_mask:
                return True
            
            if self.is_stop_requested():
                break
            if timeout > 0 and (time.monotonic() - start > timeout):
                break

        return False
        
        
    def do_command(self, function:int, address:int=0, data:int=0)->int|None:
        """
        Exacutes a CAMAC command
        - retrns None on No-Q, raises an exception on No-X, returns the data otherwise
        """

        if self.camac_node._dummy is not None:
            return self.camac_node._dummy.read()
        
        self.camac_node.open()
        
        n, a, f = self.station, address, function
        if f is None:
            raise spc.ControlException(f"CAMAC.do_command(): module does not support functionF{f} (N={n})")
        
        q, x, data, _ = CAMAC(n, a, f, data)
        if x == 0:
            #raise spc.ControlException(f"CAMAC.do_command(): CAMAC(): No-X from station {n} (F{f})")
            logging.error(f"CAMAC.do_command(): CAMAC(): No-X from station {n} (F{f})")
            return None
        if q == 0:
            return None
        
        return data
        

    ## child nodes ##
    def channel(self, address:int):
        return ChannelNode(self, address)


    def command(self, function:int, address:int=0):
        return CommandNode(self, function, address)


    
class ChannelNode(spc.ControlVariableNode):
    def __init__(self, module_node, address):
        self.module_node = module_node
        self.address = address

        
    def set(self, data:int)->int|None:
        return self.module_node.do_command(function=self.module_node.function_write, address=self.address, data=data)


    def get(self)->int|None:
        return self.module_node.do_command(function=self.module_node.function_read, address=self.address)


    
class CommandNode(spc.ControlVariableNode):
    def __init__(self, module_node, function:int, address:int=0):
        self.module_node = module_node
        self.function = function
        self.address = address

        
    def set(self, data:int)->int|None:
        return self.module_node.do_command(function=self.function, address=self.address, data=data)


    def get(self)->int|None:
        return self.module_node.do_command(function=self.function, address=self.address)




# Dummy CAMAC Device

import time, random, math


class DummyDevice:
    @staticmethod
    def normal(mean, sigma):
        u1 = random.random()
        u2 = random.random()
        r = math.sqrt(-2.0*math.log(u1)) * math.cos(2.0 * math.pi * u2)
    
        return mean + r * sigma


    @staticmethod
    def poisson(mean):
        sum = 0
        counts = -1
    
        while sum < mean:
            counts += 1
            step = random.random()
            if step == 0:
                break
            sum += -math.log(step)

        return counts

    
    @staticmethod
    def exponential(scale=1.0):
        y = random.random()
        while y == 0:
            y = random.random()
        
        return -math.log(y) * scale


    def __init__(self, rate:float=10, charge:float=3, resolution:float=0.5, gain:float=100, threshold:float=30, sn:float=3):
        self.rate = rate
        self.charge = charge
        self.resolution = resolution
        self.gain=gain
        self.threshold = threshold
        self.sn = sn


    def wait(self):
        dt = self.exponential(1/self.rate)
        time.sleep(dt)


    def read(self):
        while True:
            if (self.sn + 1) * random.random() > 1:
                q = self.gain * self.poisson(self.charge) + self.normal(0, self.gain*self.resolution)
            else:
                q = abs(self.normal(0, self.gain*self.resolution))
            if q > self.threshold:
                break
        return q


    def clear(self):
        pass


    

# camlib.py #
# Created by Sanshiro Enomoto on 9 November 2025. #

DEVICE_FILE = "/dev/camdrv"

import os, fcntl, struct, errno

_IOC_NONE = 0
_IOC_READ = 2
_IOC_WRITE = 1

_IOC_DIRSHIFT = 30
_IOC_TYPESHIFT = 8
_IOC_NRSHIFT = 0
_IOC_SIZESHIFT = 16

def _IOC(dir, type, nr, size):
    return ((dir << _IOC_DIRSHIFT) | (type << _IOC_TYPESHIFT) | (nr << _IOC_NRSHIFT) | (size << _IOC_SIZESHIFT))

def _IO(type, nr):
    return _IOC(_IOC_NONE, type, nr, 0)

def _IOR(type, nr, size):
    return _IOC(_IOC_READ, type, nr, size)

def _IOW(type, nr, size):
    return _IOC(_IOC_WRITE, type, nr, size)

def _IOWR(type, nr, size):
    return _IOC(_IOC_READ | _IOC_WRITE, type, nr, size)


_IOC_SIZE_UINT2 = 8

CAMDRV_IOC_MAGIC = 0xCC
CAMDRV_IOC_INITIALIZE = _IO(CAMDRV_IOC_MAGIC, 1)
CAMDRV_IOC_CLEAR = _IO(CAMDRV_IOC_MAGIC, 2)
CAMDRV_IOC_INHIBIT = _IO(CAMDRV_IOC_MAGIC, 3)
CAMDRV_IOC_RELEASE_INHIBIT = _IO(CAMDRV_IOC_MAGIC, 4)
CAMDRV_IOC_ENABLE_INTERRUPT = _IO(CAMDRV_IOC_MAGIC, 5)
CAMDRV_IOC_DISABLE_INTERRUPT = _IO(CAMDRV_IOC_MAGIC, 6)
CAMDRV_IOC_CAMAC_ACTION = _IOWR(CAMDRV_IOC_MAGIC, 7, _IOC_SIZE_UINT2)
CAMDRV_IOC_READ_LAM = _IOR(CAMDRV_IOC_MAGIC, 8, _IOC_SIZE_UINT2)
CAMDRV_IOC_WAIT_LAM = _IOWR(CAMDRV_IOC_MAGIC, 9, _IOC_SIZE_UINT2)
CAMDRV_IOC_SET_CRATE = _IOW(CAMDRV_IOC_MAGIC, 10, _IOC_SIZE_UINT2)


_device_descriptor = None


def COPEN():
    global _device_descriptor
    try:
        _device_descriptor = os.open(DEVICE_FILE, os.O_RDWR)
        return 0
    except OSError as e:
        return e.errno


def CCLOSE():
    global _device_descriptor
    if _device_descriptor is not None:
        try:
            os.close(_device_descriptor)
            _device_descriptor = None
            return 0
        except OSError as e:
            return e.errno
    return 0


def CSETCR(crate_number):
    if _device_descriptor is None:
        return errno.EBADF
    
    try:
        ioctl_data = struct.pack('<II', crate_number, 0)
        fcntl.ioctl(_device_descriptor, CAMDRV_IOC_SET_CRATE, ioctl_data)
        return 0
    except OSError as e:
        return e.errno


def CGENZ():
    if _device_descriptor is None:
        return errno.EBADF
    
    try:
        fcntl.ioctl(_device_descriptor, CAMDRV_IOC_INITIALIZE)
        return 0
    except OSError as e:
        return e.errno


def CGENC():
    if _device_descriptor is None:
        return errno.EBADF
    
    try:
        fcntl.ioctl(_device_descriptor, CAMDRV_IOC_CLEAR)
        return 0
    except OSError as e:
        return e.errno


def CAMAC(n, a, f, data=0):
    """
    execute a CAMAC action
    Args:
        n, a, f: number, address, function
        data: data value
    Returns:
        (q, x, data, errno)
    """
    if _device_descriptor is None:
        return (0, 0, data, errno.EBADF)
    
    try:
        naf = ((n << 9) | (a << 5) | f) & 0x3fff
        ioctl_data = bytearray(struct.pack('=II', naf, data & 0x00ffffff))
        result = fcntl.ioctl(_device_descriptor, CAMDRV_IOC_CAMAC_ACTION, ioctl_data, True)
        
        if result < 0:
            return (0, 0, 0, errno.EIO)
    except OSError as e:
        return (0, 0, data, e.errno)
        
    q = 0 if (result & 0x0001) else 1
    x = 0 if (result & 0x0002) else 1
    _, data_out = struct.unpack('=II', ioctl_data)
    data_out = data_out & 0x00ffffff

    print(f'n{n},a{a},f{f} -> data={data}, q={q}, x={x}')

    return (q, x, data_out, 0)


def CWLAM(timeout):
    """Wait for a LAM"""
    
    if _device_descriptor is None:
        return errno.EBADF
    
    try:
        ioctl_data = bytearray(struct.pack('=II', timeout, 0))
        result = fcntl.ioctl(_device_descriptor, CAMDRV_IOC_WAIT_LAM, ioctl_data, True)
    except OSError as e:
        return e.errno

    return 0 if result > 0 else errno.ETIMEDOUT


def CWLAM2(timeout):
    """Wait for a LAM and returns the LAM mask
    - throws an OSError on error
    """
    
    if _device_descriptor is None:
        return 0
    
    try:
        ioctl_data = bytearray(struct.pack('=II', timeout, 0))
        result = fcntl.ioctl(_device_descriptor, CAMDRV_IOC_WAIT_LAM, ioctl_data, True)
    except OSError as e:
        if e.errno == errno.ETIMEDOUT:
            return None
        raise

    return result if result > 0 else None



if __name__ == '__main__':
    camac = CamacNode(crate=1, dummy=False)
    module = camac.module(station=3)
    while True:
        module.wait()
        for address in range(0, 2):
            print(module.channel(address).get())
        #module.clear()
        module.command(function=10).get()
