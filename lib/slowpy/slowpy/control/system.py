# Created by Sanshiro Enomoto on 17 May 2024 #


import time, signal, dataclasses, logging
import slowpy.control as spc


class ControlSystem(spc.ControlNode):
    # this will be set by sd_taskmodule.py when a module that imports this is loaded to SlowDash App
    _slowdash_app = None
    
    # note that these class variables are app-wide: multiple task modules will share these.
    _slowdash_exports = []   # not including publish()
    _slowdash_channels = {}  # including export() and publish()
    
    def __init__(self):
        self.import_control_module('Ethernet')
        self.import_control_module('HTTP').import_control_module('Slowdash')
        self.import_control_module('Shell')
        self.import_control_module('DataStore')

        
    @classmethod
    def app(cls):
        return cls._slowdash_app


    @classmethod
    def _register_channel(cls, name, value):
        if type(value) is not dict:
            cls._slowdash_channels[name] = {'name': name, 'current': True}
            return
            
        if 'table' in value:
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
            datatype = 'json'
            
        cls._slowdash_channels[name] = {'name': name, 'type': datatype, 'current': True}

        
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
    def export(cls, obj, name:str):
        node = None
        if isinstance(obj, type):
            logging.error(f'exporting a type is not allowed')
        elif isinstance(obj, spc.ControlNode):
            node = obj
        elif type(obj) is dict:
            node = DictExportAdapterNode(obj)
        elif dataclasses.is_dataclass(obj):
            node = DataclassExportAdapterNode(obj)
        elif callable(getattr(obj, 'from_json', None)) and callable(getattr(obj, 'to_json', None)):
            node = SlowpyElementExportAdapterNode(obj)
            obj._slowdash_export_name = name
        else:
            logging.error(f'exporting a bad type object: {type(obj)}')

        if node is not None:
            cls._slowdash_exports.append((name, node))
            cls._register_channel(name, node.get())
            node._slowdash_export_name = name
            
        return node


    @classmethod
    async def publish(cls, obj, name:str=None):
        if cls.app() is None:
            return
        
        export_name = getattr(obj, '_slowdash_export_name', None)
        publish_name = name if name is not None else export_name
        if publish_name is None:
            logging.error(f'export name required')
            return
                
        value = None
        if isinstance(obj, type):
            logging.error(f'publishing a type is not allowed')
            return
        elif isinstance(obj, spc.ControlNode):
            value = obj.get()
        elif type(obj) in [ bool, int, float, str ]:
            value = obj
        elif type(obj) is dict:
            value = {'tree': obj }
        elif dataclasses.is_dataclass(obj):
            value = {'tree': dataclasses.asdict(self.value) }
        elif callable(getattr(obj, 'from_json', None)) and callable(getattr(obj, 'to_json', None)):
            value = obj.to_json()
        else:
            logging.error(f'exporting a bad type object: {type(obj)}')
            return

        # register this to channel list if not already in
        if name is not None and name != export_name:
            if name not in cls._slowdash_channels:
                cls._register_channel(name, value)
            if export_name is None:
                obj._slowdash_export_name = name
                
        record = { publish_name: { 't': time.time(), 'x': value } }
        await cls.app().request_publish('currentdata', record)

        
    # child nodes
    def value(self, initial_value=None):
        return spc.ValueNode(initial_value)
    


class ValueNode(spc.ControlVariableNode):
    def __init__(self, initial_value=None):
        if isinstance(initial_value, spc.ControlNode):
            self.value = initial_value.get()
        else:
            self.value = initial_value

        
    def set(self, value):
        self.value = value

        
    def get(self):
        return self.value


    # DEPRECIATED (July 2025): use ControlSystem.publish(obj) instead
    async def deliver(self):
        return await ControlSystem.publish(self)


                                         
class DictExportAdapterNode(spc.ControlVariableNode):
    def __init__(self, value=None):
        if not type(value) is dict:
            logging.error('dict value expected')
            self.value = None
        else:
            self.value = value
            
        
    def set(self, value):
        if type(value) != dict:
            return
        tree = value.get('tree', None)
        if type(tree) != dict:
            return
        
        if self.value is None:
            return

        if False:
            # unset filed values will be None
            for field in self.value.keys():
                self.value[field] = tree.get(field, None)
        else:
            # unset filed values will not be changed
            for k,v in tree.items():
                if k in self.value:
                    self.value[k] = v
                    
        
    def get(self):
        if self.value is not None:
            return { 'tree': self.value }
        else:
            return { 'tree': {} }



class DataclassExportAdapterNode(spc.ControlVariableNode):
    def __init__(self, dataclass_value=None):
        if not dataclasses.is_dataclass(dataclass_value) or isinstance(dataclass_value, type):
            logging.error('dataclass instance expected')
            self.value = None
        else:
            self.value = dataclass_value
            
        
    def set(self, value):
        if type(value) != dict:
            return
        tree = value.get('tree', None)
        if type(tree) != dict:
            return
        
        if self.value is None:
            return

        fields = [ f.name for f in dataclasses.fields(self.value) ]
        
        if False:
            # unset filed values will be None
            for field in fields:
                setattr(self.value, field, tree.get(field, None))
        else:
            # unset filed values will not be changed
            for k,v in tree.items():
                if k in fields:
                    setattr(self.value, k, v)
                    
        
    def get(self):
        if self.value is not None:
            return { 'tree': dataclasses.asdict(self.value) }
        else:
            return { 'tree': {} }



class SlowpyElementExportAdapterNode(spc.ControlVariableNode):
    def __init__(self, value=None):
        self.value = value
            
        
    def set(self, value):
        if type(value) == dict:
            self.value.from_json(value)
            
        
    def get(self):
        return self.value.to_json()


        
control_system = ControlSystem()
