# Created by Sanshiro Enomoto on 8 November 2024 #


import pyvisa
import slowpy.control as spc
from control_Ethernet import ScpiCommandNode


class VisaNode(spc.ControlNode):
    def __init__(self, address):
        try:
            self.instr = pyvisa.ResourceManager().open_resource(address)
        except Exception as e:
            print('VISA open error: %s' % str(e))
            self.instr = None


    def __del__(self):
        if self.instr is not None:
            self.instr.close()
            
        
    @classmethod
    def _node_creator_method(cls):
        def visa(self, address, **kwargs):
            return VisaNode(address, **kwargs)

        return visa

    
    def set(self, value):
        return self.instr.write(value)

    def get(self):
        return self.instr.read()


    def do_get_chunk(self, timeout=None):
        if timeout is None:
            return self.instr.read()
        timeout_original = self.instr.timeout
        return ''


    def do_get_line(self, timeout=None):

        
    ## child nodes ##
    def scpi(self, **kwargs):
        return VisaScpiNode(self, **kwargs)
    

    
class VisaScpiNode(spc.ControlNode):
    def __init__(self, instr, timeout=10, sync=True, append_opc=False, verbose=False):
        self.instr = instr
        self.sync = sync
        self.append_opc = append_opc
        self.verbose = verbose
        
        if timeout is not None and timeout > 0:
            self.instr.timeout = self.timeout

    
    def set(self, value=None):
        if self.verbose:
            sys.stderr.write('SCPI SET: [%s]' % value)
        return self.instr.write(value)
            
    
    def get(self):
        try:
            reply = self.instr.read()
        except pyvisa.VisaIOError as e:
            print('VISA error: %s' % str(e))
            return ''
            
        if self.verbose:
            sys.stderr.write(' --> [%s]\n' % reply)
        return reply


    ## child nodes ##
    def command(self, name, **kwargs):
        return ScpiCommandNode(self, name, **kwargs)
    
