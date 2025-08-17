# Created by Sanshiro Enomoto on 25 December 2024 #

import sys, os, copy, glob, inspect, logging, traceback
import importlib
import slowlette


class Component(slowlette.App):
    """ Base class for App components
    """
    
    def __init__(self, app, project):
        super().__init__()
        self.app = app
        self.project = project

        
    @slowlette.get('/api/config')
    def api_config(self):
        return self.public_config()


    # override this
    # TODO: remove this with using Slowlette response merging (each component/plugin binds '/config')
    def public_config(self):
        """ returns contents for the "config" API (exposed to users)
        Note:
          - Do not include secrets.
          - Do not put the configuration file contents directly (as it might contain secrets).
        """
        return {}

        
    
class ComponentPlugin(slowlette.App):
    """ Base class for plugin modules of an App component
    """
    
    def __init__(self, app, project, params):
        super().__init__()
        self.app = app
        self.project = project
        self.plugin_type = None
        self.class_name = None

    
    # override this
    def public_config(self):
        """ returns contents for the "config" API (exposed to users)
        Note:
          - Do not include secrets.
          - Do not put the configuration file contents directly (as it might contain secrets).
        """
        return {}
    


class PluginComponent(Component):
    """ App component using plugin modules
    """
    
    def __init__(self, component_type, app, project, plugin_prefix=None, class_prefix=None):
        super().__init__(app, project)

        self.component_type = component_type
        self.plugin_prefix = plugin_prefix
        self.class_prefix = class_prefix
        
        self.merge_config_params = True  # import the parameters under "params" node to the root node

        if self.plugin_prefix is None:
            # e.g., data_source -> datasource
            self.plugin_prefix = ''.join(self.component_type.split('_'))
        if self.class_prefix is None:
            # e.g., data_source -> DataSource
            self.class_prefix = ''.join([n[0].upper() + n[1:] for n in self.component_type.split('_') if len(n) > 0])
        
        plugin_config = project.config.get(self.component_type, None)
        if plugin_config is None:
            # suger: also accept a plural name
            plugin_config = project.config.get(self.component_type + 's', [])
        if not isinstance(plugin_config, list):
            plugin_config = [ plugin_config ]

        self.build(plugin_config)
        

    def public_config(self):
        """construct public_config from the member plugins.
        """

        plugins = {}
        for plugin in self.slowlette:
            name = plugin.plugin_type
            if name in plugins:
                # multiple plugins of the same type -> array
                if type(plugins[name]) is not list:
                    plugins[name] = [ plugins[name] ]
                plugins[name].append(plugin.public_config())
            else:
                plugins[name] = plugin.public_config()

        return { self.component_type: plugins }

        
    def build(self, plugin_config):
        """creates plugin instances based on the config_config
        Note:
           - this method can be overriden to modify the config contents before building
        """
        
        for node in plugin_config:
            plugin_type = node.get('type', None)
            if plugin_type is None:
                logging.error(f'No plugin type specified: {self.component_type}')
                continue
            plugin_name = f'{self.plugin_prefix}_{plugin_type}'
            class_name = f'{self.class_prefix}_{plugin_type}'
            
            if not self.merge_config_params:
                params = node.get('parameters', {})
            else:
                params = copy.deepcopy(node)
                if 'parameters' in params:
                    for k,v in params['parameters'].items():
                        params[k] = v
                    del params['parameters']
                
            plugin = self._load_plugin_module(plugin_name, class_name, params=params)
            if plugin is not None:
                plugin.plugin_type = plugin.class_name[len(self.class_prefix)+1:]
                self.slowlette.include(plugin)
                    

    def _load_plugin_module(self, plugin_name, class_name, params):
        """load a plugin module and create an instance
        Args:
          - plugin_name: name of the plugin file (case insensitive)
          - class_name: name of the class in the plugin for which an instance is created (case insensitive)
          - *args, **kwargs: parameters to the constructor
        Return:
          - instance of the class
          - None on error
        Note:
          - If the app is not async, and a plugin with "_NoAsync" suffix exits, it will be used instead.
        """
        
        plugin_dir = os.path.abspath(os.path.join(self.project.sys_dir, 'app', 'plugin'))
        no_async_plugin_name = plugin_name + '_NoAsync'

        plugin_file_name, no_async_plugin_file_name = None, None
        for plugin_file in glob.glob(os.path.join(plugin_dir, '*.py')):
            if os.path.basename(plugin_file)[:-3].lower() == plugin_name.lower():
                plugin_file_name = plugin_file
            if os.path.basename(plugin_file)[:-3].lower() == no_async_plugin_name.lower():
                no_async_plugin_file_name = plugin_file

        # fallback to NoAsync, if the server is no-async and NoAsync plugin exists
        if (not self.app.is_async) and (no_async_plugin_file_name is not None):
            plugin_file_name = no_async_plugin_file_name
            class_name += '_NoAsync'
            
        if plugin_file_name is None:
            logging.error(f'unable to find plugin: {plugin_name}')
            return None

        module = sys.modules.get(plugin_name, None)
        if module is None:
            try:
                spec = importlib.util.spec_from_file_location(plugin_name, plugin_file_name)
                module = importlib.util.module_from_spec(spec)
                sys.modules[plugin_name] = module
                spec.loader.exec_module(module)
            except Exception as e:
                logging.error(f'unable to load plugin: {plugin_file_name}: %s' % str(e))
                logging.error(traceback.format_exc())
                return None
        
        defined_classes = [
            name for name, obj in inspect.getmembers(module, inspect.isclass)
            if obj.__module__ == module.__name__
        ]
        for cls in defined_classes:
            if cls.lower() == class_name.lower():
                class_name = cls
                break
        else:
            logging.error(f'no entry found in plugin: {plugin_name}.{class_name}')
            return None
            
        try:
            instance = module.__dict__[class_name](self.app, self.project, params)
        except Exception as e:
            logging.error(f'plugin error: {plugin_name}.{class_name}: %s' % str(e))
            logging.error(traceback.format_exc())
            return None

        instance.class_name = class_name
        logging.info(f'loaded plugin {class_name}')

        return instance
