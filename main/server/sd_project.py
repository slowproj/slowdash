#! /usr/bin/env python3
# Created by Sanshiro Enomoto on 19 Mar 2022 #

import sys, os, glob, io, json, logging
import subprocess, yaml, pathlib, stat, pwd, grp, enum
from sd_version import slowdash_version


class Project:
    def __init__(self, project_dir=None, project_file=None):
        self.version = slowdash_version
        self.sys_dir = Project.find_sys_dir()
        self.project_dir = project_dir if project_dir is not None else Project.find_project_dir()
        self.config_file = project_file if project_file is not None else 'SlowdashProject.yaml'
        
        self.config = None
        self.variables = {}
        self.auth_list = None
        self.update()
        

    @classmethod
    def find_sys_dir(cls):
        target_name = 'sd_version.py'
        for path in sys.path:
            if os.path.isfile(os.path.join(path, target_name)):
                mypath = path
                break
        else:
            logging.error('unable to find Slowdash system dirctory')
            return  None
    
        return os.path.normpath(os.path.join(mypath, os.pardir, os.pardir))
    

    @classmethod
    def find_project_dir(cls):
        search_dir = os.environ.get('SLOWDASH_PROJECT', None)
        if search_dir is not None:
            search_dir = os.path.abspath(search_dir)
        else:
            search_dir = os.getcwd()

        # if SLOWDASH_PROJECT is not set, find the dir from the current directroy
        # assuming that the current directory is under the project dir
        project_dir = None
        while not project_dir and search_dir != '/':
            for dirent in os.listdir(search_dir):
                if dirent == 'SlowdashProject.yaml':
                    project_dir = search_dir
                    break
            search_dir = os.path.normpath(os.path.join(search_dir, '..'))

        if not project_dir:
            return None

        if project_dir[0] != '/':
            logging.error('invalid SLOWDASH_PROJECT: %s' % project_dir)
            return None

        return project_dir


    def update(self):
        project_conf = None
        if self.project_dir is None:
            db_url = os.environ.get('SLOWDASH_INIT_DATASOURCE_URL', None)
            if db_url is None:
                logging.error('unable to find Slowdash Project Dir: specify it with the --project-dir option, set the SLOWDASH_PROJECT environmental variable, or run the slowdash command at a project directory')
                return
            project_conf = {
                'name': 'SlowDash',
                'data_source': {
                    'url': db_url,
                    'parameters': {}
                }
            }
            ts_schema = os.environ.get('SLOWDASH_INIT_TIMESERIES_SCHEMA', None)
            if ts_schema is not None:
                project_conf['data_source']['parameters'] = {
                    'time_series': { 'schema': ts_schema }
                }
        else:
            config_file = os.path.join(self.project_dir, self.config_file)
            if not os.path.isfile(config_file):
                logging.error('unable to open project file: %s' % config_file)
                return
            with open(os.path.join(config_file)) as f:
                try:
                    config = yaml.safe_load(f)
                except Exception as e:
                    logging.error('Invalid project file syntax: %s' % str(e))
                    config = {}
                if type(config) != dict:
                    config = {}
                    
            project_conf = config.get("slowdash_project", None)
            if project_conf is None or type(project_conf) is not dict:
                logging.error('invalid project file: %s' % config_file)
                return
            
        self.config = self.process_substitution(project_conf)

        if 'name' not in self.config:
            name = os.path.basename(self.project_dir)
            if name.lower() == 'slowdash':
                name = self.project_dir.split(os.path.sep)[-2]
            self.config['name'] = name
        if 'title' not in self.config:
            name = self.config['name']
            if name.count(' ') > 0:
                title = name
            elif name.count('_') > 0:
                title = name.replace('_', ' ')
            elif name.count('-') > 0:
                title = name.replace('-', ' ')
            else:
                title = name[0]
                for k in range(1,len(name)-1):
                    if name[k].isupper() and name[k+1].islower():
                        title += ' '
                    title += name[k]
                title += name[-1]
            self.config['title'] = title
        if 'system' not in self.config:
            self.config['system'] = {}
        if self.config['system'].get('our_security_is_perfect', False):
            del self.config['system']['our_security_is_perfect']
            self.config['system']['is_secure'] = True
        else:
            self.config['system']['is_secure'] = False
            
        auth_key = self.config.get('authentication', {}).get('key', None)
        if auth_key is None:
            self.auth_list = None
        else:
            self.auth_list = {}
            
            if type(auth_key) != list:
                auth_entries = [ auth_key ]
            else:
                auth_entries = auth_key
            for auth in auth_entries:
                try:
                    (user, key) = tuple(auth.split(':', 1))
                except:
                    logging.error('Bad authentication entry: %s' % auth)
                    continue
                self.auth_list[user] = key

                
    def process_substitution(self, project_doc):
        self.variables = {}
        if 'environment' in project_doc:
            envs = self.substitute(project_doc['environment'])
            if type(envs) == list:
                for entry in envs:
                    items = entry.split('=', 1)
                    if len(items) > 1:
                        self.variables[items[0]] = items[1]
            elif type(envs) == dict:
                for k,v in envs.items():
                    self.variables[k] = v
                    
            del project_doc['environment']

        return self.substitute(project_doc)

    
    def substitute(self, doc):
        if type(doc) == dict:
            new_doc = {}
            for k,v in doc.items():
                new_doc[k] = self.substitute(v)
            return new_doc
        elif type(doc) == list:
            new_doc = []
            for v in doc:
                new_doc.append(self.substitute(v))
            return new_doc
        elif type(doc) == str:
            return self.substitute_string(doc)
        else:
            return doc

        
    def substitute_string(self, string):
        # Syntax: ......${VARIABLE}...$(COMMAND)...
        # "$$" for a single $
        
        new_string = ""
        class State(enum.Enum):
            PLAIN=1
            DOLLAR=2
            VARIABLE=3
            COMMAND=4
        state = State.PLAIN
        token = ''
        for ch in string:
            if state == State.PLAIN:
                if ch == '$':
                    state = State.DOLLAR
                else:
                    new_string += ch
            elif state == State.DOLLAR:
                if ch == '{':
                    state = State.VARIABLE
                elif ch == '(':
                    state = State.COMMAND
                else:
                    if ch == '$':
                        new_string += '$'
                    else:
                        new_string += '$' + ch
                    state = state.PLAIN
            elif state == State.VARIABLE:
                if ch == '}':
                    new_string += self.substitute_variable(token)
                    token = ''
                    state = state.PLAIN
                else:
                    token += ch
            elif state == State.COMMAND:
                if ch == ')':
                    new_string += self.substitute_command(token)
                    token = ''
                    state = state.PLAIN
                else:
                    token += ch

        return new_string

    
    def substitute_variable(self, token):
        tokens = token.split('-', 1)
        name = tokens[0]
        empty_is_null = name.endswith(':')
        if empty_is_null:
            name = name[0:-1]
        default = None if len(tokens) == 1 else tokens[1]

        value = self.variables.get(name, None)
        if value is not None and (len(value) > 0 or not empty_is_null):
            return value
            
        value = os.environ.get(name, None)
        if value is not None and len(value) == 0 and empty_is_null:
            value = None
        if value is None:
            value = default
        if value is None:
            logging.error('variable substitution error: %s' % name)
            return '${%s}' % name
        return value

        
    def substitute_command(self, token):
        try:
            result = subprocess.check_output(token, shell=True).decode()
            if len(result) > 0 and result[-1] == '\n':
                return result[:-1]
            else:
                return result
        except Exception as e:
            logging.error('command execution error: %s: %s' % (token, str(e)))
            return '$(%s)' % token
    
            
    def get(self):
        if self.config is None:
            return {}
        else:
            return {
                'system': {
                    'version': self.version,
                    'system_dir': self.sys_dir,
                },
                'project_dir': self.project_dir,
                'config': self.config
            }

    
    def write(self, output = sys.stdout):
        json.dump(self.get(), output, indent=4)
        output.write('\n')



from sd_component import Component

class ProjectComponent(Component):
    def __init__(self, app, project):
        super().__init__(app, project)
        self.project_dir = self.project.project_dir
        

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

        if path[0] != 'config':
            return None

        if len(path) == 1:
            return self.get_config(with_list=False)
            
        elif len(path) == 2:
            if path[1] == 'list':
                return self.get_config(with_list=True, with_content_meta=True)
            
            elif path[1] == 'filelist':
                sortby = opts.get('sortby', 'mtime')
                reverse = (opts.get('reverse', 'false').upper() != 'FALSE')
                return self.get_config_filelist(sortby=sortby, reverse=reverse)
                
        elif len(path) == 3:
            if path[1] == 'filemeta':
                return self.get_config_filemeta(path[2])
                
            elif (len(path) == 3) and (path[1] == 'file'):
                return self.get_config_file(path[2], output)
            
            elif (len(path) == 3) and (path[1] == 'jsonfile'):
                return self.get_config_file(path[2], output, to_json=True)

        return False


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
        
        if path[0] != 'config':
            return None
        
        if path[0] == 'config':
            if (len(path) < 3) or (path[1] != 'file'):
                return False
            else:
                return self.save_config_file(path[2], doc, opts)

        return False

            
    def process_delete(self, path):
        """ DELETE-request handler
        Args:
          path: parsed URL
        Returns:
          - HTTP response code as int
          - False for error (HTTP response 400 "Bad request")
          - None if the path is not the target (chain of responsibility)
        """

        if (len(path) < 3) or (path[0] != 'config') or (path[1] != 'file'):
            return 403  # Forbidden
        if self.project_dir is None:
            return 404  # Not Found
        
        filepath = os.path.abspath(os.path.join(self.project_dir, 'config', path[2]))
        if not (os.path.isfile(filepath) and os.access(filepath, os.W_OK)):
            return 400  # Bad Request
        
        try:
            os.remove(filepath)
        except Exception as e:
            logging.error(f'file deletion error: {filename}: %s' % str(e))
            return 500   # Internal Server Error
        
        return 200


    def get_config(self, with_list=True, with_content_meta=True):
        self.project.update()
        if self.project.config is None:
            doc = {
                'slowdash': {
                    'version': self.project.version
                },
                'project': {}
            }
        else:
            doc = {
                'slowdash': {
                    'version': self.project.version
                },
                'project': {
                    'name': self.project.config.get('name', 'Untitled Project'),
                    'title': self.project.config.get('title', ''),
                    'is_secure': self.project.config.get('system', {}).get('is_secure', False)
                },
                'style': self.project.config.get('style', None),
            }

            for components in self.app.components:
                doc.update(components.public_config() or {})
            
        if (not with_list) or (self.project_dir is None):
            return doc
        
        filelist = []
        for filepath in glob.glob(os.path.join(self.project_dir, 'config', '*-*.*')):
            filelist.append([filepath, int(os.path.getmtime(filepath))])
            filelist = sorted(filelist, key=lambda entry: entry[1], reverse=True)
                
        contents = {}
        for filepath, mtime in filelist:
            filename = os.path.basename(filepath)
            rootname, ext = os.path.splitext(os.path.basename(filepath))
            kind, name = rootname.split('-', 1)
            config_key = '%s_config' % kind
            if ext not in [ '.json', '.yaml', '.html' ]:
                continue
            if config_key not in contents:
                contents[config_key] = []

            meta_info = {}
            if with_content_meta:
                meta_info = self.get_config_filemeta(filename)

            contents[config_key].append({
                'name': name,
                'mtime': mtime,
                'title': meta_info.get('title', ''),
                'description': meta_info.get('description', ''),
                'config_file': filename,
                'config_error': meta_info.get('config_error', ''),
                'config_error_line': meta_info.get('config_error_line', '')
            })
        doc['contents'] = contents

        return doc

                
    def get_config_filemeta(self, filename):
        meta_info = {}
        
        if self.project_dir is None:
            return meta_info
        filepath = os.path.join(self.project_dir, 'config', filename)
        if not (os.path.isfile(filepath) and os.access(filepath, os.R_OK)):
            return meta_info

        ext = os.path.splitext(os.path.basename(filepath))[1]
        if ext not in [ '.json', '.yaml' ]:
            return meta_info

        if os.path.getsize(filepath) <= 0:
            meta_info['config_error'] = 'empty file'
        else:
            try:
                with open(filepath) as f:
                    this_config = yaml.safe_load(f)
                    if type(this_config) != dict:
                        meta_info['config_error'] = 'not a dict'
                    else:
                        meta_info = this_config.get('meta', {})
            except yaml.YAMLError as e:
                if hasattr(e, 'problem_mark'):
                    line = e.problem_mark.line+1
                    meta_info['config_error_line'] = line
                    meta_info['config_error'] = 'Line %d: %s' % (line, e.problem)
                else:
                    meta_info['config_error'] = str(e)

        return meta_info
                    

    def get_config_filelist(self, sortby='name', reverse=False):
        if self.project_dir is None:
            return []
        
        filelist = []
        for filepath in glob.glob(os.path.join(self.project_dir, 'config', '*.*')):
            filestat = os.lstat(filepath)
            mtime = int(os.path.getmtime(filepath))
            filelist.append({
                'name': os.path.basename(filepath),
                'size': os.path.getsize(filepath),
                'mode': stat.filemode(filestat.st_mode),
                'owner': pwd.getpwuid(filestat.st_uid)[0],
                'group': grp.getgrgid(filestat.st_gid)[0],
                'mtime': mtime
            })

        if len(filelist) > 0 and sortby in filelist[0].keys():
            filelist = sorted(filelist, key=lambda entry: entry[sortby], reverse=reverse)
            
        return filelist


    def get_config_file(self, filename, output, to_json=False):
        if self.project_dir is None:
            return {}
        is_secure = self.project.config.get('system', {}).get('is_secure', False)
        filepath = os.path.join(self.project_dir, 'config', filename)
        if not (os.path.isfile(filepath) and os.access(filepath, os.R_OK)):
            return {}
        try:
            pathlib.Path(filepath).touch()
        except:
            pass

        ext = os.path.splitext(filepath)[1].lower()
        if ext == '.json':
            content_type = 'application/json'
        elif ext == '.yaml':
            content_type = 'text/plain'
        elif ext == '.svg':
            content_type = 'image/svg+xml'
        elif ext == '.png':
            content_type = 'image/png'
        elif ext in ['.jpg', '.jpeg']:
            content_type = 'image/jpeg'
        elif ext == '.html':
            content_type = 'text/html'
        elif ext == '.csv':
            content_type = 'text/plain'
        elif is_secure and (ext == '.py'):
            content_type = 'text/plain'
        elif is_secure and (ext == '.js'):
            content_type = 'text/plain'
        else:
            return False
            
        output.flush()
        if os.path.getsize(filepath) <= 0:
            return content_type

        if to_json and (ext == '.yaml'):
            try:
                with open(filepath) as f:
                    original = yaml.safe_load(f)
                    converted = json.dumps(original, indent=4)
                    output.write(converted.encode())
                    content_type = 'application/json'
            except:
                return False
            
        else:
            output.write(io.FileIO(filepath, 'r').readall())

        return content_type


    def save_config_file(self, filename, doc, opts):
        if self.project_dir is None:
            return False
        if (len(filename) == 0) or not filename[0].isalpha():
            return False
        if not filename.replace('_', '0').replace('-', '0').replace('.', '0').replace(' ', '0').isalnum():
            return False
        is_secure = self.project.config.get('system', {}).get('is_secure', False)
        ext = os.path.splitext(filename)[1]
        if not is_secure and (ext not in [ '.json', '.yaml', '.html', '.csv', '.svn', '.png', '.jpg', '.jpeg' ]):
            return False

        config_dir = os.path.join(self.project_dir, 'config')
        if not os.path.isdir(config_dir):
            try:
                os.makedirs(config_dir)
            except:
                logging.error('unable to create directory: ' + config_dir)
                return 500       # Internal Server Error
            
        mode = self.project.config.get('system', {}).get('file_mode', 0o644) + 0o100
        if mode & 0o070 != 0:
            mode = mode + 0o010
        if mode & 0o007 != 0:
            mode = mode + 0o001
        try:
            os.chmod(config_dir, mode)
        except Exception as e:
            logging.warning('unable to change file mode (%03o): %s: %s' % (mode, config_dir, str(e)))
            
        gid = self.project.config.get('system', {}).get('file_gid', -1)
        try:
            os.chown(config_dir, -1, gid)
        except Exception as e:
            logging.warning('unable to change file gid (%d): %s: %s' % (gid, config_dir, str(e)))

        filepath = os.path.join(config_dir, filename)
        if os.path.exists(filepath):
            if not os.access(filepath, os.W_OK):
                return 403   # Forbidden
            if (opts.get('overwrite', 'no') != 'yes'):
                return 202   # Accepted: no action made, try with overwrite flag
            
        try:
            with open(filepath, "wb") as f:
                f.write(doc)
        except Exception as e:
            logging.error(f'unable to write file: {filepath}: %s' % str(e))
            return 500    # Internal Server Error

        try:
            mode = self.project.config.get('system', {}).get('file_mode', 0o644)
            os.chmod(filepath, mode)
        except Exception as e:                
            logging.warning('unable to change file mode (%03o): %s: %s' % (mode, filepath, str(e)))
        try:
            gid = self.project.config.get('system', {}).get('file_gid', -1)
            os.chown(filepath, -1, gid)
        except Exception as e:
            logging.warning('unable to change file gid (%d): %s: %s' % (gid, config_dir, str(e)))

        return 201 # Created

        

if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument(
        '--project-dir',
        action='store', dest='project_dir', default=None,
        help='project directory (default: current dir if not specified by SLOWDASH_PROJECT environmental variable)'
    )
    parser.add_argument(
        '--project-file',
        action='store', dest='project_file', default=None,
        help='project file (default: SlowdashProject.yaml file at the project directory)'
    )
    args = parser.parse_args()

    project = Project(args.project_dir, args.project_file)

    project.write()
