# Created by Sanshiro Enomoto on 17 May 2024 #


import time, signal, dataclasses, logging
import slowpy as slp
import slowpy.control as spc


class ControlSystem(spc.ControlNode):
    # this will be set by sd_taskmodule.py when a module that imports this is loaded to SlowDash App
    _slowdash_app = None
    
    # note that these class variables are app-wide: multiple task modules will share these.
    _slowdash_exports = []   # not including aio_publish()
    _slowdash_channels = {}  # including export() and aio_publish()
    
    def __init__(self):
        self.import_control_module('Ethernet')
        self.import_control_module('HTTP').import_control_module('Slowdash')
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

        if node is not None:
            cls._slowdash_exports.append((name, node))
            cls._register_channel(name, node.get())
            node.__slowdash_export_name = name
            
        return node


    @classmethod
    async def aio_publish(cls, obj, name:str=None):
        if cls.app() is None:
            return

        # special handling for Matplotlib figure
        config, data = slp.slowdashify(obj, name)
        if data is not None:
            now = time.time()
            packet = { k: { 't': now, 'x': v } for k,v in data.items() }
            await cls.app().request(f'/config/transient/content/slowplot/{name}', config)
            await cls.app().request_publish('current_data', packet, sender=f'taskmodule_{name}')
            return
        
        # value
        value, value_is_ts = None, False
        if isinstance(obj, type):
            pass
        elif isinstance(obj, spc.ControlNode):
            value = { 'tree': obj.get() }
        elif callable(getattr(obj, 'to_json', None)):  # SlowPy Element (histogram etc)
            value = obj.to_json()
            value_is_ts = isinstance(obj, slp.TimeSeries)
        elif type(obj) in [ bool, int, float, str ]:
            value = obj
        elif type(obj) is dict:
            value = {'tree': obj }
        elif dataclasses.is_dataclass(obj):
            value = { 'tree': dataclasses.asdict(obj) }
        else:
            try:
                value = {'tree': vars(obj) }
            except:
                pass
        if value is None:
            logging.error(f'bad value type to publish: {type(obj)}')
            return

        # name
        export_name = getattr(obj, '__slowdash_export_name', None)
        publish_name = name if name is not None else export_name
        if publish_name is None:
            name = cls._make_name()
            publish_name = name
                
        # register this to channel list if not already in
        if name is not None and name != export_name:
            try:
                setattr(obj, '__slowdash_export_name', name)   # using setattr() for dataclass
            except:
                pass  # obj does not have setattr()  (such as an interger)

            # published channels are now handled by subpub cache
            #if name not in cls._slowdash_channels:
            #    cls._register_channel(name, value, value_is_ts)

        if value_is_ts:
            record = { publish_name: value }
        else:
            record = { publish_name: { 't': time.time(), 'x': value } }
        await cls.app().request_publish('current_data', record, sender=f'taskmodule_{publish_name}')

        
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
            self.value = initial_value.get()
        else:
            self.value = initial_value

        if self.value is not None:
            self.VariableType = type(self.value)
        else:
            self.VariableType = None

        
    def set(self, value):
        if self.VariableType is None:
            if value is not None:
                self.VariableType = type(value)
                
        if self.VariableType is not None:
            try:
                self.value = self.VariableType(value)
            except:
                self.value = value
        else:
            self.value = value

        
    def get(self):
        return self.value


    # DEPRECIATED (July 2025): use ControlSystem.aio_publish(obj) instead
    async def deliver(self):
        return await ControlSystem.aio_publish(self)


                                         
class _DictExportAdapterNode(spc.ControlVariableNode):
    def __init__(self, value=None):
        if not type(value) is dict:
            logging.error('dict value expected')
            self.value = None
        else:
            self.value = value
            
        
    def set(self, value):
        if not type(value) is dict:
            logging.error('dict value expected')
            return
        tree = value.get('tree',value)
        
        for k, v in tree.items():
            if k in self.value and self.value[k] is not None:
                try:
                    self.value[k] = type(self.value)(v)
                except:
                    self.value[k] = v
            else:
                self.value[k] = v

            
    def get(self):
        if self.value is not None:
            return { 'tree': self.value }
        else:
            return { 'tree': {} }

        

class _DataclassInstanceExportAdapterNode(spc.ControlVariableNode):
    def __init__(self, value=None):
        if not dataclasses.is_dataclass(value) or isinstance(value, type):
            logging.error('dataclass instance expected')
            self.value = None
        else:
            self.value = value
            

    def set(self, value):
        if not type(value) is dict:
            logging.error('dict value expected')
            return
        tree = value.get('tree', value)

        ann = type(self.value).__annotations__
        for k, v in tree.items():
            if k not in ann:
                logging.error(f'undefined field "{k}" for dataclass "{type(self.value)}"')
                continue
            try:
                vv = ann[k](v)
            except:
                logging.error(f'unable to convert value "{v}" to field "{k}" of dataclass "{type(self.value)}" (type {an[k]})')
            try:
                setattr(self.value, k, vv)
            except:
                logging.error(f'unable to assign value "{v}" to field "{k}" of dataclass "{type(self.value)}"')
        
            
    def get(self):
        if self.value is not None:
            return { 'tree': dataclasses.asdict(self.value) }
        else:
            return { 'tree': {} }


        
class _ClassInstanceExportAdapterNode(spc.ControlVariableNode):
    def __init__(self, value=None):
        try:
            vars(value)
            self.value = value
        except:
            logging.error('class instance expected')
            self.value = None

            
    def set(self, value):
        if not type(value) is dict:
            logging.error('dict value expected')
            return
        tree = value.get('tree', value)
        
        for k, v in tree.items():
            if not hasattr(self.value, k) and getattr(self.value, k) is not None:
                try:
                    setattr(self.value, k, type(self.value)(v))
                except:
                    setattr(self.value, k, v)
            else:
                setattr(self.value, k, v)

            
    def get(self):
        if self.value is not None:
            return { 'tree': { k:v for k,v in vars(self.value).items() if not k.endswith('__slowdash_export_name') } }
        else:
            return { 'tree': {} }



class _SlowpyElementExportAdapterNode(spc.ControlVariableNode):
    def __init__(self, value=None):
        self.value = value

        
    def set(self, value):
        logging.error('SlowPy elements are read-only')


    def get(self):
        return self.value.to_json()


control_system = ControlSystem()
