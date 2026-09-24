# Created by Sanshiro Enomoto on 17 May 2024 #


import time, signal, dataclasses, copy, json, asyncio, logging
import slowpy as slp
import slowpy.control as spc


class ControlSystem(spc.ControlNode):
    # this will be injected by slowdash-task.py
    _tasklet = None
    
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
    def _get_name(cls, obj, name:str|None=None):
        data_name = getattr(obj, '__slowmesh_data_name', None)
        mesh_name = name if name is not None else data_name
        if mesh_name is None:
            cls._mesh_unnamed_count += 1
            name = f'unnamed{cls._mesh_unnamed_count:02d}'
            mesh_name = name
        if name is not None and name != data_name:
            try:
                setattr(obj, '__slowmesh_data_name', name)   # using setattr() for dataclass
            except:
                pass  # obj does not have setattr()  (such as an interger)

        return mesh_name

            
    @classmethod
    async def aio_stream(cls, name:str, value):
        return await cls.aio_publish(value, name=name)

    
    @classmethod
    def stream(cls, name:str, value):  # needs a loop somewhere: e.g., running from Tasklet etc.
        loop = asyncio.get_running_loop()
        loop.create_task(cls.aio_publish(value, name=name))

    
    @classmethod
    async def aio_publish(cls, obj, name:str|None=None):
        if cls._tasklet is None:
            if not cls._mesh_error_shown:
                logging.error('ControlSysten: Tasklet not attached (publish)')
                cls._mesh_error_shown = True
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
        elif isinstance(obj, ( bool, int, float, str )):
            value = obj
        elif isinstance(obj, dict):  # must be a SlowDash value
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

        mesh_name = cls._get_name(obj, name)        
        if value_is_ts:
            record = { mesh_name: value }
        else:
            record = { mesh_name: { 't': time.time(), 'x': value } }
            
        await cls._tasklet.mesh.aio_publish(f'data.stream.{mesh_name}', record)


    @classmethod
    async def aio_export(cls, obj, name:str|None=None):
        return cls.export(obj, name)

    
    @classmethod
    def export(cls, obj, name:str|None=None):
        if cls._tasklet is None:
            if not cls._mesh_error_shown:
                logging.error('ControlSysten: Tasklet not attached (export)')
                cls._mesh_error_shown = True
            return

        if not isinstance(obj, spc.ControlNode):
            logging.error(f'Bad data type to export: {name} ({type(obj)})')
            return
            
        mesh_name = cls._get_name(obj, name)
        cls._tasklet.mesh.export(mesh_name, obj)
        

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
