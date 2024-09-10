# Created by Sanshiro Enomoto on 10 September 2024 #

"""SlowPy/Control LabJack plugin
- This uses LabJack Python Library, LabJackPython. Install it by `pip LabJackPython`.
- LabJack Python for U12 uses the LabJack Exodriver library available at the LabJack web page.
"""


import slowpy.control as spc


class LabJackU12(spc.ControlNode):
    def __init__(self):
        import u12
        self.u12 = u12.U12()
        
    ## child nodes ##
    def ain(self, ch, gain=0):
        return LabjackU12_AnalogIn(self.u12, ch, gain)
    
    def aout(self, ch):
        return LabjackU12_AnalogOut(self.u12, ch)
    
    def din(self, ch):
        return LabjackU12_DigitalIn(self.u12, ch)
    
    def dout(self, ch):
        return LabjackU12_DigitalOut(self.u12, ch)
    
    @classmethod
    def _node_creator_method(cls):
        def labjack_U12(self):
            try:
                self.labjack_U12_node
            except:
                self.labjack_U12_node = LabJackU12()
            return self.labjack_U12_node

        return labjack_U12

    
    
class LabjackU12_AnalogIn(spc.ControlVariableNode):
    def __init__(self, u12, ch, gain):
        self.u12 = u12
        self.ch = int(ch)
        self.gain = int(gain)
            
    def get(self):
        return self.u12.eAnalogIn(channel=self.ch, gain=self.gain).get('voltage', None)


    
class LabjackU12_AnalogOut(spc.ControlVariableNode):
    def __init__(self, u12, ch):
        self.u12 = u12
        self.ch = int(ch)

        self.u12._aout0 = 0
        self.u12._aout1 = 0
        
            
    def set(self, value):
        if self.ch == 0:
            self.u12._aout0 = float(value) 
        elif self.ch == 1:
            self.u12._aout1 = float(value) 
        self.u12.eAnalogOut(self.u12._aout0, self.u12._aout1)

        
    def get(self):
        if self.ch == 0:
            return self.u12._aout0
        elif self.ch == 1:
            return self.u12._aout1
        else:
            return None

    
class LabjackU12_DigitalIn(spc.ControlVariableNode):
    def __init__(self, u12, ch):
        self.u12 = u12
        self.ch = int(ch)
            
    def get(self):
        return self.u12.eDigitalIn(channel=self.ch).get('state', None)


    
class LabjackU12_DigitalOut(spc.ControlVariableNode):
    def __init__(self, u12, ch):
        self.u12 = u12
        self.ch = int(ch)
        self.value = None
            
    def set(self, value):
        self.value = 1 if bool(value) else 0
        self.u12.eDigitalOut(channel=self.ch, state=self.value)

    def get(self):
        return self.value
    
