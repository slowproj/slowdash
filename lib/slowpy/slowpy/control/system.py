# Created by Sanshiro Enomoto on 17 May 2024 #


import time, signal, dataclasses, asyncio, logging
import slowpy as slp
import slowpy.control as spc


class ControlSystem(spc.ControlNode):
    # this will be injected by slowdash-task.py
    _mesh = None
    
    _mesh_error_shown = False
    _mesh_unnamed_count = 1

    
    def __init__(self):
        self.import_control_module('Ethernet')
        self.import_control_module('HTTP')
        self.import_control_module('AsyncHTTP')
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
        """enables stopping by a signal (Ctrl-c)
        """
        def handle_signal(signum, frame):
            logging.info(f'Signal {signum} handled')
            cls.stop()
        signal.signal(signal_number, handle_signal)

        
    @classmethod
    async def aio_stream(cls, name:str, value):
        return await cls.aio_publish(value, name=name)

    
    @classmethod
    def stream(cls, name:str, value):  # needs a loop somewhere: e.g., running from Tasklet etc.
        loop = asyncio.get_running_loop()
        loop.create_task(cls.aio_publish(value, name=name))

    
    @classmethod
    async def aio_publish(cls, obj, name:str|None=None):
        if cls._mesh is None:
            if not cls._mesh_error_shown:
                logging.error('Mesh not attached to the SlowPy Control system')
                cls._mesh_error_shown = True
                print(f"##### CONTROL: {cls._mesh}")
            return
        
        # name
        mesh_name = getattr(obj, '__slowmesh_data_name', None)
        publish_name = name if name is not None else mesh_name
        if publish_name is None:
            cls._mesh_unnamed_count += 1
            name = f'unnamed{cls._mesh_unnamed_count:02d}'
            publish_name = name
        if name is not None and name != mesh_name:
            try:
                setattr(obj, '__slowmesh_data_name', name)   # using setattr() for dataclass
            except:
                pass  # obj does not have setattr()  (such as an interger)

        # special handling for Matplotlib figure
        config, data = slp.slowdashify(obj, name)
        if data is not None:
            now = time.time()
            packet = { k: { 't': now, 'x': v } for k,v in data.items() }
            await cls.app().request(f'/config/transient/content/slowplot/{name}', config)
            await cls.app().request_emit('current_data', packet, sender=f'taskmodule_{name}')
            return

        # special handling for ControlNode
        if isinstance(obj, spc.ControlNode):
            obj = await obj.aio_get()
        
        # value
        value, value_is_ts = None, False
        if isinstance(obj, type):
            pass
        elif callable(getattr(obj, 'to_json', None)):  # SlowPy Element (histogram etc)
            value = obj.to_json()
            value_is_ts = isinstance(obj, slp.TimeSeries)
        elif type(obj) in [ bool, int, float, str ]:
            value = obj
        elif type(obj) is dict:  # must be a SlowDash value
            if 'tree' in obj or 'table' in obj or 'bins' in obj or 'ybin' in obj or 'y' in obj:
                value = obj
            else:
                value = {'tree': obj }  # or raise an exception...
        elif dataclasses.is_dataclass(obj):
            value = { 'tree': dataclasses.asdict(obj) }
        else:
            try:
                value = {'tree': vars(obj) }
            except:
                pass
        if (obj is not None) and (value is None):
            logging.error(f'bad value type to publish: {type(obj)}')
            return

        if value_is_ts:
            record = { publish_name: value }
        else:
            record = { publish_name: { 't': time.time(), 'x': value } }
            
        await cls._mesh.aio_publish(f'data.stream.{publish_name}', record)


    # child nodes
    def value(self, initial_value=None):
        return spc.ValueNode(initial_value)
    


class ValueNode(spc.ControlVariableNode):
    def __init__(self, initial_value=None):
        if isinstance(initial_value, spc.ControlNode):
            self._value = initial_value.get()
        else:
            self._value = initial_value

        if self._value is not None:
            self._VariableType = type(self._value)
        else:
            self._VariableType = None

        
    def set(self, value):
        if self._VariableType is None:
            if value is not None:
                self._VariableType = type(value)
                
        if self._VariableType is not None:
            try:
                self._value = self._VariableType(value)
            except:
                self._value = value
        else:
            self._value = value

        
    def get(self):
        return self._value

    
control_system = ControlSystem()
