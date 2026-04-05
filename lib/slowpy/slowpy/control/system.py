# Created by Sanshiro Enomoto on 17 May 2024 #


import time, signal, dataclasses, logging
import slowpy as slp
import slowpy.control as spc


class ControlSystem(spc.ControlNode):
    # this will be set by sd_taskmodule.py when a module that imports this is loaded to SlowDash App
    _slowdash_app = None
    
    # note that these class variables are app-wide: multiple task modules will share these.
    _slowdash_exports = []   # not including aio_emit()
    _slowdash_channels = {}  # including export() and aio_emit()
    
    def __init__(self):
        self.import_control_module('Ethernet')
        self.import_control_module('HTTP')
        self.import_control_module('AsyncHTTP')
        self.import_control_module('Shell')
        self.import_control_module('DataStore')

        
    @classmethod
    def app(cls):
        return cls._slowdash_app


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
    def export(cls, obj, name:str=None):
        node = cls._get_export_node(obj, name)
        if node is not None:
            cls._slowdash_exports.append((name, node))
            cls._register_channel(name, node.get())
            node.__slowdash_export_name = name
            
        return node


    @classmethod
    async def aio_export(cls, obj, name:str=None):
        node = cls._get_export_node(obj, name)
        if node is not None:
            cls._slowdash_exports.append((name, node))
            cls._register_channel(name, await node.aio_get())
            node.__slowdash_export_name = name
            
        return node


    @classmethod
    async def aio_emit(cls, obj, name:str=None):
        if cls.app() is None:
            return

        # name
        export_name = getattr(obj, '__slowdash_export_name', None)
        emit_name = name if name is not None else export_name
        if emit_name is None:
            name = cls._make_name()
            emit_name = name
        if name is not None and name != export_name:
            try:
                setattr(obj, '__slowdash_export_name', name)   # using setattr() for dataclass
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
            logging.error(f'bad value type to emit: {type(obj)}')
            return

        if value_is_ts:
            record = { emit_name: value }
        else:
            record = { emit_name: { 't': time.time(), 'x': value } }
        await cls.app().request_emit('current_data', record, sender=f'taskmodule_{emit_name}')

        
    # DEPRECIATED (March 2026): use aio_emit() instead
    @classmethod
    async def aio_publish(cls, obj, name:str=None):
        return await cls.aio_emit(obj, name)

        
    @classmethod
    def _get_export_node(cls, obj, name:str):
        if name is None:
            name = getattr(obj, '__slowdash_export_name', None)
        if name is None:
            name = cls._make_name()
        try:
            setattr(obj, '__slowdash_export_name', name)  # using setattr() for dataclass
        except:
            pass
        
        node = None
        if isinstance(obj, type):
            logging.error(f'exporting a type is not allowed')
        elif isinstance(obj, spc.ControlNode):
            node = obj
        elif callable(getattr(obj, 'to_json', None)):
            node = _SlowpyElementExportAdapterNode(obj)
        elif type(obj) is dict:
            node = _DictExportAdapterNode(obj)
        elif dataclasses.is_dataclass(obj):
            node = _DataclassInstanceExportAdapterNode(obj)
        else:
            try:
                vars(obj)
                node = _ClassInstanceExportAdapterNode(obj)
            except:
                logging.error(f'exporting a bad type object: {type(obj)}')

        return node

                
    @classmethod
    def _register_channel(cls, name, value, value_is_ts=False):
        if type(value) is not dict:
            cls._slowdash_channels[name] = {'name': name, 'current': True}
            return
            
        if value_is_ts:
            datatype = 'timeseries'
        elif 'table' in value:
            datatype = 'table'
        elif 'tree' in value:
            datatype = 'tree'
        elif 'bins' in value:
            datatype = 'histogram'
        elif 'ybins' in value:
            datatype = 'histogram2d'
        elif 'y' in value:
            datatype = 'graph'
        else:
            datatype = 'tree'
            
        cls._slowdash_channels[name] = {'name': name, 'type': datatype, 'current': True}


    _unnamed_count = 1

    @classmethod
    def _make_name(cls):
        name = f'unnamed{cls._unnamed_count:02d}'
        cls._unnamed_count += 1
        return name
            
    
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


    # DEPRECIATED (July 2025): use ControlSystem.aio_emit(obj) instead
    async def deliver(self):
        return await ControlSystem.aio_emit(self)


                                         
class _DictExportAdapterNode(spc.ControlVariableNode):
    def __init__(self, value=None):
        if not type(value) is dict:
            logging.error('dict value expected')
            self._value = None
        else:
            self._value = value
            
        
    def set(self, value):
        if not type(value) is dict:
            logging.error('dict value expected')
            return
        tree = value.get('tree',value)
        
        for k, v in tree.items():
            if k in self._value and self._value[k] is not None:
                try:
                    self._value[k] = type(self._value)(v)
                except:
                    self._value[k] = v
            else:
                self._value[k] = v

            
    def get(self):
        if self._value is not None:
            return { 'tree': self._value }
        else:
            return { 'tree': {} }

        

class _DataclassInstanceExportAdapterNode(spc.ControlVariableNode):
    def __init__(self, value=None):
        if not dataclasses.is_dataclass(value) or isinstance(value, type):
            logging.error('dataclass instance expected')
            self._value = None
        else:
            self._value = value
            

    def set(self, value):
        if not type(value) is dict:
            logging.error('dict value expected')
            return
        tree = value.get('tree', value)

        ann = type(self._value).__annotations__
        for k, v in tree.items():
            if k not in ann:
                logging.error(f'undefined field "{k}" for dataclass "{type(self._value)}"')
                continue
            try:
                vv = ann[k](v)
            except:
                logging.error(f'unable to convert value "{v}" to field "{k}" of dataclass "{type(self._value)}" (type {ann[k]})')
            try:
                setattr(self._value, k, vv)
            except:
                logging.error(f'unable to assign value "{v}" to field "{k}" of dataclass "{type(self._value)}"')
        
            
    def get(self):
        if self._value is not None:
            return { 'tree': dataclasses.asdict(self._value) }
        else:
            return { 'tree': {} }


        
class _ClassInstanceExportAdapterNode(spc.ControlVariableNode):
    def __init__(self, value=None):
        try:
            vars(value)
            self._value = value
        except:
            logging.error('class instance expected')
            self._value = None

            
    def set(self, value):
        if not type(value) is dict:
            logging.error('dict value expected')
            return
        tree = value.get('tree', value)
        
        for k, v in tree.items():
            if hasattr(self._value, k) and getattr(self._value, k) is not None:
                try:
                    ValueType = type(getattr(self._value, k))
                    setattr(self._value, k, ValueType(v))
                except:
                    setattr(self._value, k, v)
            else:
                setattr(self._value, k, v)

            
    def get(self):
        if self._value is not None:
            return { 'tree': { k:v for k,v in vars(self._value).items() if not k.endswith('__slowdash_export_name') } }
        else:
            return { 'tree': {} }



class _SlowpyElementExportAdapterNode(spc.ControlVariableNode):
    def __init__(self, value=None):
        self._value = value

        
    def set(self, value):
        logging.error('SlowPy elements are read-only')


    def get(self):
        return self._value.to_json()


control_system = ControlSystem()
