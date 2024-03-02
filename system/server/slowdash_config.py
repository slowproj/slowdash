#! /usr/bin/env python3
# Created by Sanshiro Enomoto on 19 Mar 2022 #

import sys, os, subprocess, logging, enum, json, yaml

slowdash_version = '0.0.1'

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s %(levelname)s: %(message)s', 
    datefmt='%y-%m-%d %H:%M:%S'
)


def find_sys_dir():
    myname = 'slowdash_config.py'
    for path in sys.path:
        if os.path.isfile(os.path.join(path, myname)):
            mypath = path
            break
    else:
        logging.error('unable to find Slowdash system dirctory')
        return  None
    
    return os.path.normpath(os.path.join(mypath, os.pardir, os.pardir))
    

def find_project_dir():
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
        logging.warn('unable to find Slowdash Project Dir: specify it with the --project-dir option, set the SLOWDASH_PROJECT environmental variable, or run the slowdash command at a project directory')
        return None

    if project_dir[0] != '/':
        logging.error('invalid SLOWDASH_PROJECT: %s' % project_dir)
        return None

    return project_dir



class Config:
    def __init__(self, project_dir=None):
        self.auth_list = None
        
        self.version = slowdash_version
        self.sys_dir = find_sys_dir()
        if self.sys_dir is not None:
            self.bin_dir = os.path.join(self.sys_dir, 'bin')
            self.doc_dir = os.path.join(self.sys_dir, 'doc')
        else:
            self.bin_dir = None
            self.doc_dir = None
            
        if project_dir is not None:
            self.project_dir = project_dir
        else:
            self.project_dir = find_project_dir()
        self.project = None

        self.variables = {}
        
        if self.sys_dir is None or self.project_dir is None:
            return

        self.project_dir = os.path.abspath(self.project_dir)
        try:
            os.chdir(self.project_dir)
        except Exception as e:
            logging.error('unable to move to project dir "%s": %s' % (self.project_dir, str(e)))            
            self.project_dir = None
            return
            
        self.update()
        

    def update(self):
        if self.project_dir is None:
            return
        
        project_file = os.path.join(self.project_dir, 'SlowdashProject.yaml')
        if not os.path.isfile(project_file):
            project_file = os.path.join(self.project_dir, 'SlowdashProject.json')
            if not os.path.isfile(project_file):
                logging.error('unable to find project file: %s' % project_file)
                return
            
        with open(os.path.join(project_file)) as f:
            try:
                config = yaml.safe_load(f)
            except Exception as e:
                logging.error('Invalid Configuration File: %s' % str(e))
                config = {}
        project_conf = config.get("slowdash_project", None)
        if (project_conf is None) or type(project_conf) is not dict :
            logging.error('invalid Slowdash project file: %s' % project_file)
            return
        self.project = self.process_substitution(project_conf)

        if 'name' not in self.project:
            name = os.path.basename(self.project_dir)
            if name.lower() == 'slowdash':
                name = self.project_dir.split(os.path.sep)[-2]
            self.project['name'] = name
            if 'title' not in self.project:
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
                self.project['title'] = title
                
            
        auth_key = self.project.get('authentication', {}).get('key', None)
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
        if self.project is None:
            return {}
        else:
            return {
                'system': {
                    'version': self.version,
                    'system_dir': self.sys_dir,
                },
                'project_dir': self.project_dir,
                'project': self.project
            }

    
    def write(self, output = sys.stdout):
        json.dump(self.get(), output, indent=4)
        output.write('\n')



if __name__ == '__main__':
    config = Config()
    if not config.project_dir:
        config.write()
