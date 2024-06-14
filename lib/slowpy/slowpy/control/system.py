
import time, signal, logging
from slowpy.control import ControlNode



class ControlSystem(ControlNode):
    def __init__(self):
        self.load_control_module('Ethernet')

        
    @classmethod
    def stop(cls):
        cls._stop_event.set()

        
    @classmethod
    def sleep(cls, duration_sec):
        sec10 = int(10*duration_sec)
        subsec10 = 10*duration_sec - sec10
        if sec10 > 0:
            for i in range(sec10):
                if cls.is_stop_requested():
                    return False
                else:
                    time.sleep(0.1)
        elif subsec10 > 0:
            time.sleep(subsec/10.0)

        return not cls.is_stop_requested()


    @classmethod
    def stop_by_signal(cls, signal_number=signal.SIGINT):
        def handle_signal(signum, frame):
            cls.stop()
        signal.signal(signal_number, handle_signal)
        
