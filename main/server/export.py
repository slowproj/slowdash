#! /usr/bin/env python3
# Created by Sanshiro Enomoto on 20 March 2022 #

import sys, os, glob, datetime, logging, traceback
import component


class Export:
    def __init__(self, app, project, **params):
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



class ExportComponent(component.Component):
    def __init__(self, app, project):
        super().__init__(app, project)
        
        self.export_table = {}
        
        export_node = project.config.get('export', [])
        if not isinstance(export_node, list):
            export_node = [ export_node ]

        if len(export_node) == 0:
            export_node.append({
                'type': 'notebook'
            })
            
        for node in export_node:
            name = node.get('type', None)
            params = node.get('parameters', {})
            if name is None:
                continue
            export = self.load_plugin_module(f'Export_{name}', **params)
            if export is not None:
                self.export_table[name] = export
                    

    def public_config(self):
        return {
            "export": { name: export.public_config() for name, export in self.export_table.items() }
        }

        
    def process_get(self, path, opts, output):
        if len(path) < 2 or path[0] != 'export':
            return None
        
        for name, export in self.export_table.items():
            result = export.process_get(path, opts, output)
            if result is not None:
                return result
            
        return None


    def process_post(self, path, opts, doc, output):
        if len(path) < 2 or path[0] != 'export':
            return None
        
        for name, export in self.export_table.items():
            result = export.process_post(path, opts, doc, output)
            if result is not None:
                return result
            
        return None
