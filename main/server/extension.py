#! /usr/bin/env python3
# Created by Sanshiro Enomoto on 20 March 2022 #

import sys, os, glob, datetime, logging, traceback
import importlib.machinery


class ExtensionModule:
    def __init__(self, project_config, module_config):
        self.project_config = project_config
        self.config = module_config

        
    # override this
    def process_get(self, path, opts, output):
        """ GET-request handler
        Args:
          path & opts: parsed URL, as list & dict
          doc: posted contents
          output: file-like object to write response content, if return value is not a dict
        Returns:
          either:
            - contents as Python dict, to reply as JSON string with HTTP response 200
            - content-type (MIME) as string, with reply contents written in output
            - HTTP response code as int
            - None for error
        """

        return 404   # Not found

    
    # override this
    def process_post(self, path, opts, doc, output):
        """ POST-request handler
        Args:
          path & opts: parsed URL, as list & dict
          doc: posted contents
          output: file-like object to write response content, if return value is not a dict
        Returns:
          either:
            - contents as Python dict, to reply as JSON string with HTTP response 201
            - content-type (MIME) as string, with reply contents written in output
            - HTTP response code as int
            - None for error
        """
        
        return 500   # Internal Server Error

        
def load(name, project_config, module_config, slowdash):
    module_dir = os.path.abspath(os.path.join(project_config.sys_dir, 'main', 'plugin'))
    plugin_name = None
    for plugin_file in glob.glob(os.path.join(module_dir, 'api_*.py')):
        plugin_name = os.path.basename(plugin_file)[4:-3]
        if plugin_name.lower() == name.lower():
            break
    if plugin_name is None:
        logging.error('unable to find API extension plugin: %s' % name)
        return None
        
    plugin_file = 'api_%s.py' % plugin_name
    file_path = os.path.abspath(os.path.join(module_dir, plugin_file))
    try:
        module = importlib.machinery.SourceFileLoader(plugin_file, file_path).load_module()
    except Exception as e:
        logging.error('unable to load API extension plugin: %s: %s' % (plugin_name, str(e)))
        logging.error(traceback.format_exc())
        return None
    logging.debug('loaded API extension plugin "%s"' % plugin_name)

    extension = None
    class_name = 'Extension_%s' % plugin_name
    if class_name in module.__dict__:
        extension = module.__dict__[class_name](project_config, module_config, slowdash)
    else:
        logging.error('no entry found in API extension: %s' % plugin_name)
        
    return extension
