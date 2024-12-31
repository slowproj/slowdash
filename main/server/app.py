#! /usr/bin/env python3
# Created by Sanshiro Enomoto on 3 Sep 2021 #


import sys, os, io, json, logging
import project, component, datasource, export, usermodule, taskmodule


class App:
    def __init__(self, project_dir=None, project_file=None, is_cgi=False, is_command=False):
        self.project = project.Project(project_dir, project_file)
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

        ### Console Redirect ###
        self.console_outputs = []
        self.original_stdin = sys.stdin
        self.original_stdout = sys.stdout
        if not is_command and not is_cgi:
            self.console_stdin = io.StringIO()
            self.console_stdout = io.StringIO()
            sys.stdin = self.console_stdin
            sys.stdout = self.console_stdout
        else:
            self.console_stdin = None
            self.console_stdout = None
            
        # API Components
        self.components.append(project.ProjectComponent(self, self.project))
        self.components.append(datasource.DataSourceComponent(self, self.project))
        self.components.append(export.ExportComponent(self, self.project))
        self.components.append(usermodule.UserModuleComponent(self, self.project))
        self.components.append(taskmodule.TaskModuleComponent(self, self.project))

                
    def __del__(self):
        del self.components
        
        if self.console_stdout is not None:
            self.console_stdin.close()
            self.console_stdout.close()
            sys.stdin = self.original_stdin
            sys.stdout = self.original_stdout
            
        logging.info('cleanup completed')


    def terminate(self):
        for component in reversed(self.components):
            component.terminate()
            
        
    def process_get(self, path, opts, output):
        """ GET-request handler
        Args:
          path & opts: parsed URL, as list & dict
          output: file-like object to write response content, if return value is not a dict
        Returns:
          either:
            - contents as Python dict or list, to reply as a JSON string with HTTP response 200
            - content-type (MIME) as string, with reply contents written in output
            - HTTP response code as int
            - None or False for error
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
            
        if result is not None:
            return result
        
        if len(path) > 0 and path[0] == 'console':
            if self.console_stdout is not None:
                self.console_outputs += [ line for line in self.console_stdout.getvalue().split('\n') if len(line)>0 ]
                self.console_stdout.seek(0)
                self.console_stdout.truncate(0)
                self.console_stdout.seek(0)
                if len(self.console_outputs) > 10000:
                    self.console_outputs = self.console_outputs[-10000:]
                output.write('\n'.join(self.console_outputs[-20:]).encode())
            else:
                output.write('[no console output]'.encode())
            output.flush()
            return 'text/plain'
                
        if len(path) > 1 and path[0] == 'authkey':
            name = path[1]
            word = opts.get('password', '')
            try:
                import bcrypt
            except:
                logging.error('install python module "bcrypt"')
                return None
            key = bcrypt.hashpw(word.encode("utf-8"), bcrypt.gensalt(rounds=12, prefix=b"2a")).decode("utf-8")
            result = { 'type': 'Basic', 'key':  '%s:%s' % (name, key) }
            
        return result
        

    def process_post(self, path, opts, doc, output):
        """ POST-request handler
        Args:
          path & opts: parsed URL, as list & dict
          doc: posted contents (binary block)
          output: file-like object to write response content, if return value is not a dict
        Returns:
          either:
            - contents as Python dict or list, to reply as a JSON string with HTTP response 201
            - content-type (MIME) as string, with reply contents written in output
            - HTTP response code as int
            - None for error
        """

        # Only first output is returned
        for component in self.components:
            result = component.process_post(path, opts, doc, output)
            if result is not None:
                return result

        if len(path) > 0 and path[0] == 'console':
            cmd = doc.decode()
            if cmd is None:
                return 400  # Bad Request
            logging.info(f'Console Input: {cmd}')
            pos = self.console_stdin.tell()
            self.console_stdin.seek(0, io.SEEK_END)
            self.console_stdin.write('%s\n' % cmd)
            self.console_stdin.seek(pos)
            output.write(json.dumps({'status': 'ok'}).encode())
            return 'application/json'
        
        return 400  # Bad Request

    
    def process_delete(self, path):
        """ DELETE-request handler
        Args:
          path: parsed URL
        Returns:
          HTTP response code as int
        """
        
        # Only first delete is performed
        for component in self.components:
            result = component.process_delete(path)
            if result is not None:
                return result

        return 400  # Bad Request
