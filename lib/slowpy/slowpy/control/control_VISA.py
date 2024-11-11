# Created by Sanshiro Enomoto on 8 November 2024 #

# BUG: timeout not implemented


import sys, time
import pyvisa
import slowpy.control as spc


class VisaNode(spc.ControlNode):
    def __init__(self, resource_name):
        try:
            self.rm = pyvisa.ResourceManager()
            self.instr = self.rm.open_resource(resource_name)
        except Exception as e:
            print('VISA open error: %s' % str(e))
            self.instr = None


    def __del__(self):
        if self.instr is not None:
            self.instr.close()
            self.rm.close()
            
            
    @classmethod
    def _node_creator_method(cls):
        def visa(self, resource_name, **kwargs):
            return VisaNode(resource_name, **kwargs)

        return visa

    
    def set(self, value):
        if self.instr is None:
            return

        #self.instr.timeout = 86400000 # 1 day
        try:
            self.instr.write(value)
        except pyvisa.VisaIOError as e:
            print('VISA error on write: %s' % str(e))

            
    def get(self, timeout=None):
        if self.instr is None:
            return None

        #if timeout is not None and float(timeout) > 0:
        #    wait_until = time.time() + timeout
        #    self.instr.timeout = 1000  # 1 sec
        #else:
        #    wait_until = None
        #    self.instr.timeout = 86400000 # 1 day

        reply = None
        #while not self.is_stop_requested():
        if not self.is_stop_requested():
            try:
                reply = self.instr.read().rstrip('\n')
            except pyvisa.VisaIOError as e:
                #if e.error_code == pyvisa.constants.VI_ERROR_TMO:
                #    if wait_until is None or time.time() < wait_until:
                #        continue
                print('VISA error on read: %s' % str(e))
                return None
        
        return reply

    
    ## child nodes ##
    def scpi(self, **kwargs):
        return VisaScpiNode(self, **kwargs)
    

    
class VisaScpiNode(spc.ControlNode):
    def __init__(self, visa, timeout=10, sync=True, append_opc=False, verbose=False):
        self.visa = visa
        self.timeout = timeout
        self.sync = sync
        self.append_opc = append_opc
        self.verbose = verbose

        
    def set(self, value):
        if self.verbose:
            sys.stderr.write('SCPI SET: [%s]' % value)
            
        write_value = value + '\n' if len(value) > 0 and value[-1] != '\n' else value
        
        return self.visa.set(value)
            
    
    def get(self):
        reply = self.visa.get(timeout=self.timeout)
        
        if self.verbose:
            sys.stderr.write(' --> [%s]\n' % reply)
            
        return reply


    ## child nodes ##
    def command(self, name, **kwargs):
        return spc.ScpiCommandNode(self, name, **kwargs)
    
