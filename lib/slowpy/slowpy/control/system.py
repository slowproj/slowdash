
import signal, logging
from slowpy.control import ControlNode


class ControlSystem(ControlNode):
    def __init__(self):
        self.import_control_module('Ethernet')
        self.import_control_module('Shell')

        
    @classmethod
    def stop(cls):
        cls._stop_event.set()

        
    @classmethod
    def stop_by_signal(cls, signal_number=signal.SIGINT):
        def handle_signal(signum, frame):
            cls.stop()
        signal.signal(signal_number, handle_signal)
