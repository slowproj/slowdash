# Created by Sanshiro Enomoto on 4 February 2025 #


import sys, time, serial, logging
import slowpy.control as spc


class SerialNode(spc.ControlNode):
    def __init__(self, port='/dev/ttyUSB0', baudrate=115200, polling_interval=1, **kwargs):
        self.com = None
        kwargs['timeout'] = polling_interval
        
        try:
            import serial
        except Exception as e:
            logging.error('unable to import serial: pyserial not installed?')
            return
        
        try:
            self.com = serial.Serial(port, baudrate, **kwargs)
        except Exception as e:
            print('Serial open error: %s' % str(e))
            self.com = None


    def __del__(self):
        if self.com is not None:
            self.com.close()
            
            
    @classmethod
    def _node_creator_method(cls):
        def serial(self, port='/dev/ttyUSB0', baudrate=115200, **kwargs):
            return SerialNode(port, baudrate, **kwargs)

        return serial

    
    def set(self, value):
        if self.com is None:
            return

        try:
            if type(value) == bytes:
                self.com.write(value)
            else:
                self.com.write(str(value).encode('utf-8'))
        except Exception as e:
            logging.error('Serial error on write: %s' % str(e))

            
    def get(self, timeout=10):
        if self.com is None:
            return None
        
        return self.do_get_line(timeout=timeout)

    
    ## methods ##    
    def do_get_chunk(self, timeout=None):
        if self.com is None:
            return ''

        line = ''
        while self.com.in_waiting > 0:
            line += self.com.read(self.com.in_waiting).decode('utf-8', errors='ignore')

        return line


    def do_get_line(self, timeout=None):
        if self.com is None:
            return ''

        if timeout is not None:
            wait_until = time.time() + timeout
        else:
            wait_until = None
        
        line = ''
        while not self.is_stop_requested():
            ch = self.com.read().decode('utf-8', errors='ignore')
            
            if len(ch) == 0:
                if wait_until is not None and time.time() >= wait_until:
                    print('SerialNode.do_get_line(): timeout')
                    break

            if ch not in [ '\x0a', '\x0d' ]:
                line += ch
            else:
                break
                
        return line


    def do_flush_input(self):
        if self.com is not None:
            self.com.reset_input_buffer()
            

    ## child nodes ##
    def scpi(self, **kwargs):
        return spc.ScpiNode(self, **kwargs)
