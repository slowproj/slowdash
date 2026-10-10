# Created by Sanshiro Enomoto on 17 May 2024 #


import time, signal, dataclasses, copy, json, asyncio, logging
import slowpy as slp
import slowpy.control as spc


class ControlSystem(spc.ControlNode):
    # this will be injected by slowdash-task.py
    _tasklet = None

    @classmethod
    def bind_tasklet(cls, tasklet):
        cls._tasklet = tasklet
        
    
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

    
    # keep this for backwards compatibility...
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
        elif isinstance(obj, (slp.DataElement, slp.TimeSeries)):
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
    async def aio_expose(cls, name:str, obj):
        return cls.expose(name, obj)

    
    @classmethod
    def expose(cls, name:str, obj):
        if cls._tasklet is None:
            if not cls._mesh_error_shown:
                logging.error('ControlSysten: Tasklet not attached (export)')
                logging.info('  hint: call export() within initialize(), or call bind_tasklet() explicitly')
                cls._mesh_error_shown = True
            return
        if isinstance(obj, type):
            logging.error(f'exporting a type is not allowed')
            return

        node = None
        if isinstance(obj, spc.ControlNode):
            node = obj
        elif isinstance(obj, slp.DataElement):  # not including slp.TimeSeries, as it cannot be a "value"
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
        
        if node is None:
            logging.error(f'Bad data type to export: {name} ({type(obj)})')
            return

        mesh_name = cls._get_name(node, name)
        cls._tasklet.mesh.export(mesh_name, node)
        

    # child nodes
    def form(self, name:str):
        return FormNode(self._tasklet, name)
    

    def value(self, initial_value=None):
        return ValueNode(initial_value)
    


class FormNode(spc.ControlNode):
    def __init__(self, tasklet, name:str):
        self._tasklet = tasklet
        self._name = name

        
    async def aio_set(self, value):
        if isinstance(value, dict):
            for k, v in value.items():
                record = { 'form': self._name, 'element': k, 'value': v }
                await self._tasklet.mesh.aio_publish(f'form.{self._name}.{k}', record)
        else:
            logging.error(f'invalid form value: dict value is expected: {value}')

        
    async def aio_get(self):
        elements = await self._tasklet.mesh.registry.aio_get(f'pubsub.form.{self._name}.>', {})
        if isinstance(elements, dict):
            return { k: v['value'] for k, v in elements.items() if 'value' in v }
        else:
            return elements   # this should not happen...

        
    def element(self, name:str):
        return FormElementNode(self, name)


        
class FormElementNode(spc.ControlNode):
    def __init__(self, form_node, name:str):
        self._form_node = form_node
        self._name = name

        
    async def aio_set(self, value):
        return await self._form_node.aio_set({self._name: value})

        
    async def aio_get(self):
        form = await self._form_node.aio_get()
        if isinstance(form, dict):
            return form.get(self._name, None)
        else:
            logging.error(f'invalid form values: {form}')
            return None


        
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

    

class _SlowpyElementExportAdapterNode(spc.ControlVariableNode):
    def __init__(self, value:slp.DataElement):
        self._value = value

        
    def set(self, value):
        logging.error('SlowPy elements are read-only')
        return None


    def get(self):
        return self._value.to_json()



class _DataclassInstanceExportAdapterNode(spc.ControlVariableNode):
    def __init__(self, value):
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


        
class _DictExportAdapterNode(spc.ControlVariableNode):
    def __init__(self, value):
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



control_system = ControlSystem()
