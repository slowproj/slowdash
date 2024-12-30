#! /usr/bin/env python3
# Created by Sanshiro Enomoto on 3 Sep 2021 #


import sys, os, io, time, glob, json, logging
import project, component, datasource, export
import usermodule, taskmodule


class App:
    def __init__(self, project_dir=None, project_file=None, is_cgi=False, is_command=False):
        self.project = project.Project(project_dir, project_file)
        self.project_dir = self.project.project_dir
        self.is_cgi = is_cgi

        self.components = []

        self.console_stdin = None
        self.console_stdout = None
        self.error_message = ''
        
        # Running Environment
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
        self.components.append(project.ProjectComponent(self, self.project))
        self.components.append(datasource.DataSourceComponent(self, self.project))
        self.components.append(export.ExportComponent(self, self.project))



        
        #... WIP: these will be moved to "components"
        self.usermodule_list = []
        self.taskmodule_list = []
        self.known_task_list = []
        

        
        ### User Modules ###
        
        usermodule_node = self.project.config.get('module', [])
        if not isinstance(usermodule_node, list):
            usermodule_node = [ usermodule_node ]
            
        for node in usermodule_node:
            if not isinstance(node, dict) or 'file' not in node:
                self.error_message = 'bad user module configuration'
                logging.error(self.error_message)
                continue
            if self.is_cgi and node.get('cgi_enabled', False) != True:
                continue
            filepath = node['file']
            params = node.get('parameters', {})
            module = usermodule.UserModule(filepath, filepath, params)
            if module is None:
                self.error_message = 'Unable to load user module: %s' % filepath
                logging.error(self.error_message)
            else:
                module.auto_load = node.get('auto_load', True)
                self.usermodule_list.append(module)


        ### Task Modules ###
        
        taskmodule_node = self.project.config.get('task', [])
        if not isinstance(taskmodule_node, list):
            taskmodule_node = [ taskmodule_node ]
                    
        task_table = {}
        for node in taskmodule_node:
            if not isinstance(node, dict):
                self.error_message = 'bad control module configuration'
                logging.error(self.error_message)
                continue
            if self.is_cgi and node.get('cgi_enabled', False) != True:
                continue
            if 'name' not in node:
                self.error_message = 'name is required for control module'
                logging.error(self.error_message)
                continue

            name = node['name']
            filepath = node.get('file', './config/slowtask-%s.py' % name)
            params = node.get('parameters', {})
            task_table[name] = (filepath, params, {'auto_load':node.get('auto_load', False)})
            self.known_task_list.append(name)
        
        # make task entries from file list of the config dir
        if not self.is_cgi and self.project_dir is not None:
            for filepath in glob.glob(os.path.join(self.project_dir, 'config', 'slowtask-*.py')):
                rootname, ext = os.path.splitext(os.path.basename(filepath))
                kind, name = rootname.split('-', 1)
                if name not in self.known_task_list:
                    task_table[name] = (filepath, {}, {'auto_load':False})
                    self.known_task_list.append(name)

        for name, (filepath, params, opts) in task_table.items():
            module = taskmodule.TaskModule(filepath, name, params)
            if module is None:
                self.error_message = 'Unable to load control module: %s' % filepath
                logging.error(self.error_message)
            else:
                module.auto_load = opts.get('auto_load', False)
                self.taskmodule_list.append(module)

                
        ### Console Redirect ###
        
        self.console_outputs = []
        self.original_stdin = sys.stdin
        self.original_stdout = sys.stdout
        if not is_command and not self.is_cgi:
            self.console_stdin = io.StringIO()
            self.console_stdout = io.StringIO()
            sys.stdin = self.console_stdin
            sys.stdout = self.console_stdout
        else:
            self.console_stdin = None
            self.console_stdout = None

            
        ### Starting Modules ###
        
        if not is_command:
            for module in self.usermodule_list + self.taskmodule_list:
                if module.auto_load:
                    module.start()

                
    def __del__(self):
        for module in self.usermodule_list + self.taskmodule_list:
            module.stop()
        self.usermodule_list.clear()
        self.taskmodule_list.clear()

        if self.console_stdout is not None:
            self.console_stdin.close()
            self.console_stdout.close()
            sys.stdin = self.original_stdin
            sys.stdout = self.original_stdout
            
        logging.info('cleanup completed')

        
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

        


        
        if path[0] == 'channels':
            result = self._get_channels()
                
        elif path[0] in ['data'] and len(path) >= 2:
            try:
                channels = path[1].split(',')
                length = float(opts.get('length', '3600'))
                to = float(opts.get('to', int(time.time())+1))
                resample = float(opts.get('resample', -1))
                reducer = opts.get('reducer', 'last')
            except Exception as e:
                logging.error(e)
                return None
            if resample < 0:
                resample = None
            result = self._get_data(channels, length, to, resample, reducer)
            
        elif path[0] == 'control':
            if len(path) >= 2 and path[1] == 'task':
                result = self._get_task_status(path, opts)
            
        elif path[0] == 'console':
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
                
        elif path[0] == 'authkey' and len(path) >= 2:
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

        for component in self.components:
            result = component.process_post(path, opts, doc, output)
            if result is not None:
                return result



            
        if path[0] == 'update' and len(path) > 1:
            target = path[1]
            if target == 'tasklist':
                if not self.is_cgi:
                    self._scan_task_files()
                return 'text/plain'
            else:
                return 400  # Bad Request
            
        elif path[0] == 'control':
            return self._dispatch_control(path, opts, doc, output)
        
        elif path[0] == 'console':
            cmd = doc.decode()
            if cmd is None:
                return 400  # Bad Request
            logging.info(f'CMD: {cmd}')
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
        
        for component in self.components:
            result = component.process_post(path, opts, doc, output)
            if result is not None:
                return result

        return None


    def _get_channels(self):
        result = []
        for src_list in [ self.usermodule_list, self.taskmodule_list ]:
            for src in src_list:
                channels = src.get_channels()
                if channels is not None:
                    result.extend(channels)

        return result

    
    def _get_data(self, channels, length, to, resample, reducer):
        result = {}
        start = to - length
        t = time.time() - start
        if t >= 0 and t <= length + 10:
            for module_list in [ self.usermodule_list, self.taskmodule_list ]:
                for module in module_list:
                    for ch in channels:
                        data = module.get_data(ch)
                        if data is None:
                            continue
                        result[ch] = {
                            'start': start, 'length': length,
                            't': t,
                            'x': data
                        }

        return result

    
    def _dispatch_control(self, path, opts, doc, output):
        """ control request handler
        Args:
          path & opts: parsed URL, as list & dict
          doc: posted contents
          output: file-like object to write response content
        Returns:
          either:
            - content-type (MIME) as string
            - HTTP response code as int
            - None for error
        """
        
        try:
            record = json.loads(doc.decode())
        except Exception as e:
            logging.error('control: JSON decoding error: %s' % str(e))
            return 400 # Bad Request
        
        result = None
        if len(path) == 1:
            logging.info("DISPATCH: %s" % str(record))
            result = self._dispatch_command(record, opts)
            
        elif path[1] == 'task':
            if len(path) >= 3:
                name = path[2]
            else:
                name = None
            logging.info("TASK COMMAND: %s.%s" % ('' if name is None else name, str(record)))
            result = self._control_task(name, record, opts)

        if result is None:
            return 400  # Bad Request
        if type(result) is str:
            output.write(result.encode())
        elif type(result) is dict:
            output.write(json.dumps(result).encode())
        elif type(result) is bool:
            if result:
                doc = {'status': 'ok'}
            else:
                doc = {'status': 'error'}
            output.write(json.dumps(doc).encode())
        else:
            try:
                output.write(str(result).encode())
            except:
                return 500   # Internal Server Error

        return 'application/json'

        
    def _dispatch_command(self, doc, opts):
        # user module first, to give the user module a change to modify the command
        for module in self.usermodule_list:
            result = module.process_command(doc)
            if result is not None:
                return result

        for module in self.taskmodule_list:
            result = module.process_command(doc)
            if result is not None:
                return result
            
        return None

    
    def _scan_task_files(self):
        if self.project_dir is None:
            return
        
        for filepath in glob.glob(os.path.join(self.project_dir, 'config', 'slowtask-*.py')):
            rootname, ext = os.path.splitext(os.path.basename(filepath))
            kind, name = rootname.split('-', 1)
            if name in self.known_task_list:
                continue
            self.known_task_list.append(name)

            module = taskmodule.TaskModule(filepath, name, {})
            if module is None:
                self.error_message = 'Unable to load control module: %s' % filepath
                logging.error(self.error_message)
            else:
                module.auto_load = False
                self.taskmodule_list.append(module)

    
    def _get_task_status(self, params, opts):
        result = []
        for module in self.taskmodule_list:
            last_routine = module.routine_history[-1] if len(module.routine_history) > 0 else None
            last_command = module.command_history[-1] if len(module.command_history) > 0 else None
            record = {
                'name': module.name,
                'is_loaded': module.is_loaded(),
                'is_routine_running': module.is_running(),
                'is_command_running': module.is_command_running(),
                'is_waiting_input': module.is_waiting_input(),
                'is_stopped': module.is_stopped(),
                'last_routine_time': last_routine[0] if last_routine is not None else None,
                'last_routine': last_routine[1] if last_routine is not None else None,
                'last_command_time': last_command[0] if last_command is not None else None,
                'last_command': last_command[1] if last_command is not None else None,
                'last_log': '',
                'has_error': module.error is not None
            }
            result.append(record)

        return result

    
    def _control_task(self, name, doc, opts):
        action = doc.get('action', None)
        for module in self.taskmodule_list:
            if module.name == name:
                if action == 'start':
                    module.start()
                    return True
                elif action == 'stop':
                    module.stop()
                    return True
                else:
                    return False
                
        return None
