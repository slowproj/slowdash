# Created by Sanshiro Enomoto on 17 May 2024 #


import signal
from slowpy.control import ControlNode


class ControlSystem(ControlNode):
    def __init__(self):
        self.import_control_module('Ethernet')
        self.import_control_module('HTTP').import_control_module('Slowdash')
        self.import_control_module('Shell')

        
    @classmethod
    def stop(cls):
        cls._global_stop_event.set()

        
    @classmethod
    def stop_by_signal(cls, signal_number=signal.SIGINT):
        def handle_signal(signum, frame):
            print(f'Signal {signum} handled')
            cls.stop()
        signal.signal(signal_number, handle_signal)
