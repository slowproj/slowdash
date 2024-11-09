# Created by Sanshiro Enomoto on 8 November 2024 #


import sys
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
            
        
    @classmethod
    def _node_creator_method(cls):
        def visa(self, resource_name, **kwargs):
            return VisaNode(resource_name, **kwargs)

        return visa

    
    def set(self, value):
        return self.instr.write(value)

    def get(self):
        return self.instr.read()

    ## child nodes ##
    def scpi(self, **kwargs):
        return VisaScpiNode(self, **kwargs)
    

    
class VisaScpiNode(spc.ControlNode):
    def __init__(self, visa, timeout=10, sync=True, append_opc=False, verbose=False):
        self.visa = visa
        self.sync = sync
        self.append_opc = append_opc
        self.verbose = verbose
        
        if self.visa.instr is not None and timeout is not None and timeout > 0:
            self.visa.instr.timeout = 1000*timeout

            
    def set(self, value=None):
        if self.visa.instr is None:
            return
        if self.verbose:
            sys.stderr.write('SCPI SET: [%s]' % value)
        try:
            return self.visa.instr.write(value)
        except pyvisa.VisaIOError as e:
            print('VISA error on write: %s' % str(e))
            return
            
    
    def get(self):
        if self.visa.instr is None:
            return None
        try:
            reply = self.visa.instr.read()
        except pyvisa.VisaIOError as e:
            print('VISA error on read: %s' % str(e))
            return ''
            
        if self.verbose:
            sys.stderr.write(' --> [%s]\n' % reply)
        return reply


    ## child nodes ##
    def command(self, name, **kwargs):
        return spc.ScpiCommandNode(self, name, **kwargs)
    
