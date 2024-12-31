#! /usr/bin/env python3
# Created by Sanshiro Enomoto on 3 Sep 2021 #


import sys, os, io, json, logging

from sd_project import Project, ProjectComponent
from sd_console import ConsoleComponent
from sd_datasource import DataSourceComponent
from sd_export import ExportComponent
from sd_usermodule import UserModuleComponent
from sd_taskmodule import TaskModuleComponent
from sd_misc_api import MiscApiComponent


class App:
    def __init__(self, project_dir=None, project_file=None, is_cgi=False, is_command=False):
        self.project = Project(project_dir, project_file)
        self.project_dir = self.project.project_dir
        self.is_cgi = is_cgi
        self.is_command = is_command

        self.components = []
        self.console_stdin = None
        self.console_stdout = None
        
        # Execution Environment
        if self.project.config is None:
            return
        
        if self.project.project_dir is not None:
            try:
                os.chdir(self.project.project_dir)
            except Exception as e:
                logging.error('unable to move to project dir "%s": %s' % (self.project.project_dir, str(e)))            
                self.project.project_dir = None
        if self.project.sys_dir is not None:
            sys.path.insert(1, os.path.join(self.project.sys_dir, 'main', 'plugin'))
        if self.project.project_dir is not None:
            sys.path.insert(1, self.project.project_dir)
            sys.path.insert(1, os.path.join(self.project.project_dir, 'config'))

        # API Components
        self.components.append(ConsoleComponent(self, self.project))   # this must be the first
        self.components.append(ProjectComponent(self, self.project))
        self.components.append(DataSourceComponent(self, self.project))
        self.components.append(ExportComponent(self, self.project))
        self.components.append(UserModuleComponent(self, self.project))
        self.components.append(TaskModuleComponent(self, self.project))
        self.components.append(MiscApiComponent(self, self.project))

                
    def __del__(self):
        del self.components
        logging.info('cleanup completed')


    def terminate(self):
        """graceful terminate
          - used by components that have a thread (usermodule/taskmodule), to send a stop request etc.
        """
        for component in reversed(self.components):
            component.terminate()
            
        
    def process_get(self, path, opts, output):
        """ GET-request handler
        Args:
          path & opts: parsed URL, as list & dict
          output: file-like object to write response content, if return value is not a dict
        Returns:
          either:
            - contents as Python dict or list, to reply as a JSON string with HTTP response 200 (OK)
            - content-type (MIME) as string, with reply contents written in output
            - HTTP response code as int
            - False for error
            - None for not-applicable
        """

        # Outputs from multiple components are merged
        result = None
        for component in self.components:
            this_result = component.process_get(path, opts, output)
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
        """ POST-request handler
        Args:
          path & opts: parsed URL, as list & dict
          doc: posted contents (binary block)
          output: file-like object to write response content, if return value is not a dict
        Returns:
          either:
            - contents as Python dict or list, to reply as a JSON string with HTTP response 201 (Created)
            - content-type (MIME) as string, with reply contents written in output
            - HTTP response code as int
            - False for error
            - None for not-applicable
        """

        # Only first output is returned
        for component in self.components:
            result = component.process_post(path, opts, doc, output)
            if result is not None:
                return result

        return 400  # Bad Request

    
    def process_delete(self, path):
        """ DELETE-request handler
        Args:
          path: parsed URL
        Returns:
          either:
            - HTTP response code as int
            - False for error
            - None for not-applicable
        """
        
        # Only first delete is performed
        for component in self.components:
            result = component.process_delete(path)
            if result is not None:
                return result

        return 400  # Bad Request
