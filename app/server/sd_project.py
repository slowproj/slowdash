# Created by Sanshiro Enomoto on 19 Mar 2022 #

import sys, os, subprocess, yaml, enum, logging
from sd_version import slowdash_version


class Project:
    def __init__(self, project_dir=None, project_file=None):
        self.version = slowdash_version
        self.sys_dir = Project.find_sys_dir()
        self.project_dir = project_dir if project_dir is not None else Project.find_project_dir()
        self.config_file = project_file if project_file is not None else 'SlowdashProject.yaml'
        self.is_secure = False
        
        self.config = None
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
            
        self.config = Substitution().process(project_conf)

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
        self.is_secure = self.config['system'].get('our_security_is_perfect', False)
            
        auth_key = self.config.get('authentication', {}).get('key', None)
        if auth_key is None:
            self.auth_list = None
        elif type(auth_key) != list:
            self.auth_list = [ auth_key ]
        else:
            self.auth_list = auth_key


            
class Substitution:
    def __init__(self):
        self._variables = {}

    def process(self, doc):
        self.variables = {}
        if 'environment' in doc:
            self._process_envs(doc)

        return self._substitute(doc)
            

    def _process_envs(self, doc):
        envs = self._substitute(doc['environment'])
        if type(envs) == list:
            for entry in envs:
                items = entry.split('=', 1)
                if len(items) > 1:
                    self._variables[items[0]] = items[1]
        elif type(envs) == dict:
            for k,v in envs.items():
                self._variables[k] = v
                    
        del doc['environment']

    
    def _substitute(self, doc):
        if type(doc) == dict:
            new_doc = {}
            for k,v in doc.items():
                new_doc[k] = self._substitute(v)
            return new_doc
        elif type(doc) == list:
            new_doc = []
            for v in doc:
                new_doc.append(self._substitute(v))
            return new_doc
        elif type(doc) == str:
            return self._substitute_string(doc)
        else:
            return doc

        
    def _substitute_string(self, string):
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
                    new_string += self._substitute_variable(token)
                    token = ''
                    state = state.PLAIN
                else:
                    token += ch
            elif state == State.COMMAND:
                if ch == ')':
                    new_string += self._substitute_command(token)
                    token = ''
                    state = state.PLAIN
                else:
                    token += ch

        return new_string

    
    def _substitute_variable(self, token):
        tokens = token.split('-', 1)
        name = tokens[0]
        empty_is_null = name.endswith(':')
        if empty_is_null:
            name = name[0:-1]
        default = None if len(tokens) == 1 else tokens[1]

        value = self._variables.get(name, None)
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

        
    def _substitute_command(self, token):
        try:
            result = subprocess.check_output(token, shell=True).decode()
            if len(result) > 0 and result[-1] == '\n':
                return result[:-1]
            else:
                return result
        except Exception as e:
            logging.error('command execution error: %s: %s' % (token, str(e)))
            return '$(%s)' % token

        
                
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

    import json
    print(json.dumps({
        'version': project.version,
        'system_dir': project.sys_dir,
        'is_secure': project.is_secure,
        'project_dir': project.project_dir,
        'config': project.config
    }))
        
