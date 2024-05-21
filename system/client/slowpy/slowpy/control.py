import os, importlib, logging, traceback


class Endpoint:
    def __init__(self, parent=None):
        self.parent = parent

    # override this as needed
    def set(self, value):
        if parent:
            parent.set(value)

    # override this as needed
    def get(self):
        if parent:
            return parent.get()
        else:
            return None

    # override this as needed
    def __str__(self):
        return str(self.get())
    
    # override this as needed
    def __float__(self):
        return float(self.get())

    # override this as needed
    @classmethod
    def _endpoint_creator_method(MyClass):
        def endpoint(self, *args, **kwargs):  # "self" is a parent (the node to which this method is added)
            return MyClass(self, *args, **kwargs)
        return endpoint

    
    @classmethod
    def add_endpoint(cls, EndpointClass, name=None):
        method = EndpointClass._endpoint_creator_method()
        if name is None:
            name = method.__name__
        setattr(cls, name, method)

        
    @classmethod
    def load_endpoint_module(cls, module_name, search_dirs=[]):
        filename = 'control_%s.py' % module_name
        if search_dirs is None or len(search_dirs) == 0:
            search_dirs = [
                os.path.abspath(os.getcwd()),
                os.path.abspath(os.path.dirname(__file__))
            ]
        for module_dir in search_dirs:
            filepath = os.path.join(module_dir, filename)
            if os.path.isfile(filepath):
                break
        else:
            logging.error('unable to find control plugin: %s' % module_name)
            return None
        
        try:
            module = importlib.machinery.SourceFileLoader(filename, filepath).load_module()
        except Exception as e:
            logging.error('unable to load control module: %s: %s' % (module_name, str(e)))
            logging.error(traceback.format_exc())
            return None
        
        logging.debug('loaded control module "%s"' % module_name)

        export_func = module.__dict__.get('export', None)
        if export_func is not None:
            for func in export_func():
                cls.add_endpoint(func)
        else:
            endpoint_classes = []
            for name, entry in module.__dict__.items():
                if callable(entry):
                    if '_endpoint_creator_method' in dir(entry):
                        endpoint_classes.append(entry)
            if len(endpoint_classes) > 1:
                cls.add_endpoint(endpoint_classes[1])
            else:
                logging.error('unable to identify Endpoint class: %s' % module_name)

        

class ControlSystem(Endpoint):
    def __init__(self):
        self.load_endpoint_module('Ethernet')
