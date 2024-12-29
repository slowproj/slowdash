#! /usr/bin/env python3
# Created by Sanshiro Enomoto on 25 December 2024 #

import sys, os, glob, logging, traceback
import importlib.machinery


class Component:
    def __init__(self, app, project):
        self.app = app
        self.project = project

        
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
            - contents as Python dict, to reply as a JSON string with HTTP response 200
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
            - contents as Python dict, to reply as a JSON string with HTTP response 201
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
          - False for error (HTTP response 400 "Bad request")
          - None if the path is not the target (chain of responsibility)
        """

        return None
        

    
class ComponentPlugin:
    def __init__(self, app, project, **params):
        self.app = app
        self.project = project

    
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
            - contents as Python dict, to reply as a JSON string with HTTP response 200
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
            - contents as Python dict, to reply as a JSON string with HTTP response 201
            - content-type (MIME) as string, with reply contents written in output
            - HTTP response code as int
            - False for error (HTTP response 400 "Bad request")
            - None if the path is not the target (chain of responsibility)
        """
        
        return None



class PluginComponent(Component):
    def __init__(self, component_type, app, project):
        super().__init__(app, project)
        self.component_type = component_type
        self.plugin_table = {}
        
        self.plugin_config = project.config.get(self.component_type, [])
        if not isinstance(self.plugin_config, list):
            self.plugin_config = [ self.plugin_config ]

        self.build()
        

    def build(self):
        """creates plugin instances based on the config stored in self.plugin_config
        Note:
           - this method can be overriden to modify the config contents before building
        """
        
        self.plugin_table = {}
        
        for node in self.plugin_config:
            plugin_name = node.get('type', None)
            if plugin_name is None:
                continue
            class_name = f'{self.component_type[0].upper()}{self.component_type[1:]}_{plugin_name}'
            params = node.get('parameters', {})
            plugin = self._load_plugin_module(f'{class_name}', **params)
            if plugin is not None:
                self.plugin_table[plugin_name] = plugin
                    

    def public_config(self):
        """construct public_config from the member plugins.
        """
        
        return {
            self.component_type: { name: plugin.public_config() for name, plugin in self.plugin_table.items() }
        }

        
    def process_get(self, path, opts, output):
        """propagates Component.process_get() to Plugin.process_get()
        """
        
        if len(path) < 2 or path[0] != self.component_type:
            return None
        
        for name, plugin in self.plugin_table.items():
            result = plugin.process_get(path, opts, output)
            if result is not None:
                return result
            
        return None


    def process_post(self, path, opts, doc, output):
        """propagates Component.process_post() to Plugin.process_post()
        """
        
        if len(path) < 2 or path[0] != self.component_type:
            return None
        
        for name, plugin in self.plugin_table.items():
            result = plugin.process_post(path, opts, doc, output)
            if result is not None:
                return result
            
        return None


    def _load_plugin_module(self, name, *args, **kwargs):
        """load a plugin module and create an instance
        Args:
          - name: name of the plugin file (case insensitive) and the class
          - *args, **kwargs: parameters to the constructor
        Return:
          - instance of the class "name"
          - None on error
        """
        
        plugin_dir = os.path.abspath(os.path.join(self.project.sys_dir, 'main', 'plugin'))
        for plugin_file in glob.glob(os.path.join(plugin_dir, '*.py')):
            plugin_name = os.path.basename(plugin_file)[:-3]
            if plugin_name.lower() == name.lower():
                break
        else:
            logging.error(f'unable to find plugin: {name}')
            return None

        try:
            module = importlib.machinery.SourceFileLoader(plugin_file, plugin_file).load_module()
        except Exception as e:
            logging.error(f'unable to load plugin: {name}: %s' % str(e))
            logging.error(traceback.format_exc())
            return None

        if name not in module.__dict__:
            logging.error(f'no entry found in plugin: {name}')
            return None
            
        try:
            instance = module.__dict__[name](self.app, self.project, *args, **kwargs)
        except Exception as e:
            logging.error(f'plugin error: {name}: %s' % str(e))
            logging.error(traceback.format_exc())
            return None
        
        logging.info('loaded plugin "%s"' % name)

        return instance
