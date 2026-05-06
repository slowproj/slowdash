# Created by Sanshiro Enomoto on 10 September 2024 #

"""SlowPy/Control LabJack plugin for U6 and U12
- This uses LabJack Python Library, LabJackPython. Install it by `pip install LabJackPython`.
- LabJack Python for U6/U12 uses the LabJack Exodriver library available at the LabJack web page.
  [Web Page](https://support.labjack.com/docs/exodriver-downloads-for-ud-series-linux-and-macos-)
  [Download (Apr 2026)](https://github.com/labjack/exodriver/archive/refs/heads/master.zip)
  $ sudo apt install libusb-1.0-0-dev
  $ cd exodriver-master
  $ sudo ./install.sh
"""


import slowpy.control as spc


class LabJackU6(spc.ControlNode):
    def __init__(self):
        import u6
        self.u6 = u6.U6()


    def close(self):
        if self.u6:
            self.u6.close()
            self.u6 = None
            
        
    ## child nodes ##
    def config(self):
        return LabjackU6_Config(self)
    
    def ain(self, ch:int, *, resolution:int=0, gain:int=0, differential:bool=False)->float:
        """Analog In
        Arguments (see U6.getAIN())
          ch (int): 0..13
          resolutoin(int): { 0:default, 1:16bit, ..., 8:19bit }
          gain (int): { 0:x1, 1:x10, 2:x100, 3:x1000, 15:auto_range }
          differential (bool): if True, channel ch+1 (odd) is paired for negative input
        """
        return LabjackU6_AnalogIn(self, ch, gain=gain, differential=differential)

    
    @classmethod
    def _node_creator_method(cls):
        def labjack_U6(self):
            try:
                self.labjack_U6_node
            except:
                self.labjack_U6_node = LabJackU6()
            return self.labjack_U6_node

        return labjack_U6

        
class LabjackU6_Config(spc.ControlVariableNode):
    def __init__(self, labjack_node):
        self.labjack_node = labjack_node
            
    def get(self):
        return self.labjack_node.u6.configU6()

    
class LabjackU6_AnalogIn(spc.ControlVariableNode):
    def __init__(self, labjack_node, ch, *, gain, differential):
        self.labjack_node = labjack_node
        self.ch = int(ch)
        self.gain = int(gain)
        self.differential = bool(differential)
            
    def get(self):
        return self.labjack_node.u6.getAIN(self.ch, gainIndex=self.gain, differential=self.differential)


    
    
class LabJackU12(spc.ControlNode):
    def __init__(self):
        import u12
        self.u12 = u12.U12()
        
    ## child nodes ##
    def ain(self, ch:int, gain:int=0)->float:
        """Analog In
        Arguments (see U12 User's Guide, "EAnalogIn"):
          ch: { 0..7: single-ended, 8..11: differential }
          gain: { 0..7: x1,x2,x4,x5,x8,x10,x16,x20 }, valid only for the differential channels
        """
        return LabjackU12_AnalogIn(self.u12, ch, gain)
    
    def aout(self, ch):
        return LabjackU12_AnalogOut(self.u12, ch)
    
    def din(self, ch):
        return LabjackU12_DigitalIn(self.u12, ch)
    
    def dout(self, ch):
        return LabjackU12_DigitalOut(self.u12, ch)
    
    def dbin(self, ch):
        return LabjackU12_DigitalIn(self.u12, ch, for_db25=True)
    
    def dbout(self, ch):
        return LabjackU12_DigitalOut(self.u12, ch, for_db25=True)
    
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
    def __init__(self, u12, ch, for_db25=False):
        self.u12 = u12
        self.ch = int(ch)
        self.readD = 1 if for_db25 else 0
            
    def get(self):
        return self.u12.eDigitalIn(channel=self.ch, readD=self.readD).get('state', None)


    
class LabjackU12_DigitalOut(spc.ControlVariableNode):
    def __init__(self, u12, ch, for_db25=False):
        self.u12 = u12
        self.ch = int(ch)
        self.writeD = 1 if for_db25 else 0
        self.value = None
            
    def set(self, value):
        self.value = 1 if bool(value) else 0
        self.u12.eDigitalOut(channel=self.ch, writeD=self.writeD, state=self.value)

    def get(self):
        return self.value

    


if __name__ == '__main__':
    if True:
        labjack = LabJackU6()
        print(labjack.config().get())
        for ch in range(8):
            print(f'AIN{ch}: {labjack.ain(ch, gain=3)}')
        for ch in range(4):
            print(f'AIN{ch}: {labjack.ain(2*ch, gain=3, differential=True)}')
            
    elif True:
        labjack = LabJackU12()
        for ch in range(8):
            print(f'AIN{ch}: {labjack.ain(ch)}')
        for ch in range(8,12):
            print(f'AIN{ch}: {labjack.ain(ch, gain=7)}')
        
