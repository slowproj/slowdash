# Created by Sanshiro Enomoto on 17 May 2024 #


import time, signal, logging
import slowpy.control as spc


class ControlSystem(spc.ControlNode):
    # this will be set by sd_taskmodule.py when a module that imports this is loaded to SlowDash App
    _slowdash_app = None
    
    def __init__(self):
        self.import_control_module('Ethernet')
        self.import_control_module('HTTP').import_control_module('Slowdash')
        self.import_control_module('Shell')
        self.import_control_module('DataStore')

        
    @classmethod
    def stop(cls):
        cls._system_stop_event.set()

        
    @classmethod
    def is_stop_requested(cls):
        return cls._system_stop_event.is_set()

    
    @classmethod
    def stop_by_signal(cls, signal_number=signal.SIGINT):
        def handle_signal(signum, frame):
            logging.info(f'Signal {signum} handled')
            cls.stop()
        signal.signal(signal_number, handle_signal)

        
    @classmethod
    async def dispatch(cls, url, body=None):
        if cls._slowdash_app is None:
            return None
        await cls._slowdash_app.dispatch(url, body)

    
    # child nodes
    def value(self, initial_value=None):
        return spc.ValueNode(initial_value)
    


class ValueNode(spc.ControlVariableNode):
    def __init__(self, initial_value=None):
        if isinstance(initial_value, spc.ControlNode):
            self.value = initial_value.get()
        else:
            self.value = initial_value
            
        # this will be assigned by _export() in sd_taskmodule.py
        self.export_name = None  

        
    def set(self, value):
        self.value = value

        
    def get(self):
        return self.value


    async def deliver(self):
        if self.export_name is None:
            logging.error('SlowPy.ValueNode.deliver(): unable to deliver as node is not exported')
            self.export_name = False
        if self.export_name is False:
            return
        
        record = {
            self.export_name: {
                't': time.time(),
                'x': self.value,
            }
        }
        
        await ControlSystem.dispatch(f'/api/publish/currentdata', record)
