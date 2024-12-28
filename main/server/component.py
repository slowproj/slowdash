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
        

    # use this in a child class
    def load_plugin_module(self, name, *args, **kwargs):
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
            
        try:
            instance = module.__dict__[name](self.app, self.project, *args, **kwargs)
        except Exception as e:
            logging.error(f'plugin error: {name}: %s' % str(e))
            logging.error(traceback.format_exc())
            return None
        
        logging.info('loaded plugin module "%s"' % name)

        return instance
