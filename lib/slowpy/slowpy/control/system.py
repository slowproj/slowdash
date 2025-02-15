# Created by Sanshiro Enomoto on 17 May 2024 #


import signal
import slowpy.control as spc


class ControlSystem(spc.ControlNode):
    def __init__(self):
        self.import_control_module('Ethernet')
        self.import_control_module('HTTP').import_control_module('Slowdash')
        self.import_control_module('Shell')
        self.import_control_module('DataStore')

        
    @classmethod
    def stop(cls):
        cls._system_stop_event.set()

        
    @classmethod
    def stop_by_signal(cls, signal_number=signal.SIGINT):
        def handle_signal(signum, frame):
            print(f'Signal {signum} handled')
            cls.stop()
        signal.signal(signal_number, handle_signal)

        
    @classmethod
    def is_stop_requested(cls):
        return cls._system_stop_event.is_set()

        
    # child nodes
    def value(self, initial_value=None):
        return spc.ValueNode(initial_value)
    
