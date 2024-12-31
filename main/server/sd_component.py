#! /usr/bin/env python3
# Created by Sanshiro Enomoto on 25 December 2024 #

import sys, os, copy, glob, inspect, logging, traceback
import importlib.machinery


class Component:
    """ Base class for App components
    """
    
    def __init__(self, app, project):
        self.app = app
        self.project = project

        
    def __del__(self):
        self.terminate()

                    
    # override this
    def terminate(self):
        pass

    
    # override this
    def public_config(self):
        """ returns contents for the "config" API (exposed to users)
        Note:
          - Do not include secrets.
          - Do not put the configuration file contents directly (as it might contain secrets).
        """
        return {}

        
    # override this
    def process_get(self, path, opts, output):
        """ GET-request handler
        Args:
          path & opts: parsed URL, as list & dict
          output: file-like object to write response content, if return value is not a dict
        Returns:
          either:
            - contents as Python dict, to reply as a JSON string with HTTP response 200 (OK)
            - content-type (MIME) as string, with reply contents written in output
            - HTTP response code as int
            - False for error (HTTP response 400 "Bad request")
            - None if the path is not the target (chain of responsibility)
        """

        return None

    
    # override this
    def process_post(self, path, opts, doc, output):
        """ POST-request handler
        Args:
          path & opts: parsed URL, as list & dict
          doc: posted contents
          output: file-like object to write response content, if return value is not a dict
        Returns:
          either:
            - contents as Python dict, to reply as a JSON string with HTTP response 201 (Created)
            - content-type (MIME) as string, with reply contents written in output
            - HTTP response code as int
            - False for error (HTTP response 400 "Bad request")
            - None if the path is not the target (chain of responsibility)
        """
        
        return None


    # override this
    def process_delete(self, path):
        """ DELETE-request handler
        Args:
          path: parsed URL
        Returns:
          - HTTP response code as int
          - None if the path is not the target (chain of responsibility)
        """

        return None
        

    
class ComponentPlugin:
    """ Base class for plugin modules of an App component
    """
    
    def __init__(self, app, project, params):
        self.app = app
        self.project = project

    
    def __del__(self):
        self.terminate()

        
    # override this
    def terminate(self):
        pass

    
    # override this
    def public_config(self):
        """ returns contents for the "config" API (exposed to users)
        Note:
          - Do not include secrets.
          - Do not put the configuration file contents directly (as it might contain secrets).
        """
        return {}

        
    # override this
    def process_get(self, path, opts, output):
        """ GET-request handler
        Args:
          path & opts: parsed URL, as list & dict
          output: file-like object to write response content, if return value is not a dict
        Returns:
          either:
            - contents as Python dict, to reply as a JSON string with HTTP response 200 (OK)
            - content-type (MIME) as string, with reply contents written in output
            - HTTP response code as int
            - False for error (HTTP response 400 "Bad request")
            - None if the path is not the target (chain of responsibility)
        """

        return None

    
    # override this
    def process_post(self, path, opts, doc, output):
        """ POST-request handler
        Args:
          path & opts: parsed URL, as list & dict
          doc: posted contents
          output: file-like object to write response content, if return value is not a dict
        Returns:
          either:
            - contents as Python dict, to reply as a JSON string with HTTP response 201 (Created)
            - content-type (MIME) as string, with reply contents written in output
            - HTTP response code as int
            - False for error (HTTP response 400 "Bad request")
            - None if the path is not the target (chain of responsibility)
        """
        
        return None



class PluginComponent(Component):
    """ App component using plugin modules
    """
    
    def __init__(self, component_type, app, project, plugin_prefix=None, class_prefix=None):
        super().__init__(app, project)

        self.component_type = component_type
        self.plugin_prefix = plugin_prefix
        self.class_prefix = class_prefix
        
        self.merge_config_params = True
        self.match_api_root = True

        if self.plugin_prefix is None:
            # e.g., data_source -> datasource
            self.plugin_prefix = ''.join(self.component_type.split('_'))
        if self.class_prefix is None:
            # e.g., data_source -> DataSource
            self.class_prefix = ''.join([n[0].upper() + n[1:] for n in self.component_type.split('_') if len(n) > 0])
        
        plugin_config = project.config.get(self.component_type, [])
        if not isinstance(plugin_config, list):
            plugin_config = [ plugin_config ]

        self.plugin_table = {}
        self.build(plugin_config)
        

    def terminate(self):
        for name, plugin in self.plugin_table.items():
            plugin.terminate()
        self.plugin_table = {}

    
    def public_config(self):
        """construct public_config from the member plugins.
        """
        
        return {
            self.component_type: { name: plugin.public_config() for name, plugin in self.plugin_table.items() }
        }

        
    def process_get(self, path, opts, output):
        """propagates Component.process_get() to Plugin.process_get()
        """
        if self.match_api_root and (len(path) < 2 or path[0] != self.component_type):
            return None

        result = None
        for name, plugin in self.plugin_table.items():
            this_result = plugin.process_get(path, opts, output)
            if type(this_result) is list:
                if result is None:
                    result = []
                elif type(result) != list:
                    logging.error('%s: incompatible results cannot be combined (list)' % name)
                    continue
                result.extend(this_result)
            elif type(this_result) is dict:
                if result is None:
                    result = {}
                elif type(result) != dict:
                    logging.error('%s: incompatible results cannot be combined (dict)' % name)
                    continue
                result.update(this_result)
            elif this_result is not None:
                if result is not None:
                    logging.error('%s: incompatible results cannot be combined (not list/dict)' % name)
                    continue
                return this_result
        
        return result


    def process_post(self, path, opts, doc, output):
        """propagates Component.process_post() to Plugin.process_post()
        """
        
        if self.match_api_root and (len(path) < 2 or path[0] != self.component_type):
            return None
        
        for name, plugin in self.plugin_table.items():
            result = plugin.process_post(path, opts, doc, output)
            if result is not None:
                return result
            
        return None


    def build(self, plugin_config):
        """creates plugin instances based on the config_config
        Note:
           - this method can be overriden to modify the config contents before building
        """
        
        self.plugin_table = {}
        
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
                self.plugin_table[plugin_name] = plugin
                    

    def _load_plugin_module(self, plugin_name, class_name, params):
        """load a plugin module and create an instance
        Args:
          - plugin_name: name of the plugin file (case insensitive)
          - class_name: name of the class in the plugin for which an instance is created (case insensitive)
          - *args, **kwargs: parameters to the constructor
        Return:
          - instance of the class
          - None on error
        """
        
        plugin_dir = os.path.abspath(os.path.join(self.project.sys_dir, 'main', 'plugin'))
        for plugin_file in glob.glob(os.path.join(plugin_dir, '*.py')):
            if os.path.basename(plugin_file)[:-3].lower() == plugin_name.lower():
                break
        else:
            logging.error(f'unable to find plugin: {plugin_name}')
            return None

        try:
            module = importlib.machinery.SourceFileLoader(plugin_file, plugin_file).load_module()
        except Exception as e:
            logging.error(f'unable to load plugin: {plugin_name}: %s' % str(e))
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
        
        logging.info(f'loaded plugin {class_name}')

        return instance
