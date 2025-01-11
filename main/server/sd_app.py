# Created by Sanshiro Enomoto on 3 Sep 2021 #


import sys, os, io, json, logging
from decimal import Decimal
from urllib.parse import urlparse, parse_qsl, unquote

from sd_project import Project, ProjectComponent
from sd_console import ConsoleComponent
from sd_datasource import DataSourceComponent
from sd_export import ExportComponent
from sd_usermodule import UserModuleComponent
from sd_taskmodule import TaskModuleComponent
from sd_misc_api import MiscApiComponent



class Reply:
    def __init__(self, response, content_type=None, content=None):
        self.response = response
        self.content_type = content_type
        self.content = content
        self.content_readable = None

        
    def __del__(self):
        if self.content_readable:
            self.content_readable.close()

            
    def get_content(self):
        if self.content_readable is not None:
            self.content = b''
            try:
                while True:
                    chunk = self.content_readable.read(1024*1024)
                    if not chunk:
                        break
                    self.content += chunk
            except Exception as e:
                logging.warning('error on sending out a reply: %s' % str(e))

            try:
                self.content_readable.close()
            except:
                pass
            self.content_readable = None

        if self.content is None:
            return b''
        elif type(self.content) is str:
            return self.content.encode()
        else:
            return self.content

        
    def write_to(self, output):
        if self.content_readable is not None:
            try:
                while True:
                    chunk = self.content_readable.read(1024*1024)
                    if not chunk:
                        break
                    output.write(chunk)
            except Exception as e:
                logging.warning('error on sending out a reply: %s' % str(e))

            try:
                self.content_readable.close()
            except:
                pass
            self.content_readable = None
        
        else:
            if self.content is None:
                pass
            elif type(self.content) is str:
                output.write(self.content.encode())
            else:
                output.write(self.content)
            return


class App:
    def __init__(self, project_dir=None, project_file=None, is_cgi=False, is_command=False, json_kwargs={}):
        self.project = Project(project_dir, project_file)
        self.project_dir = self.project.project_dir
        self.is_cgi = is_cgi
        self.is_command = is_command
        self.json_kwargs = json_kwargs

        self.components = []
        self.console_stdin = None
        self.console_stdout = None
        
        self.auth_list = self.project.auth_list

        
        # To convert decimal values into numbers that can be handled by JSON
        def decimal_to_num(obj):
            if isinstance(obj, Decimal):
                return int(obj) if float(obj).is_integer() else float(obj)
        self.json_kwargs['default'] = decimal_to_num

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


    def parse_url(self, url):
        """parses the URL and returns a tuple of "path" as list and "options" as a dict
        Args:
        - url: string
        Returns:
        - (path, options) where path is a list and options is a dict
        - (None, None) for error
        """
        accept_for_key = '_-.'
        accept_for_path = accept_for_key + ',: []'
        accept_for_value = accept_for_path + '/~;'
        def check_sanity(string, accept):
            for ch in accept:
                string = string.replace(ch, '0')
            return string.isalnum()

        u = urlparse(url)
        path = [ unquote(p) for p in u.path.split('/') ]
        while path.count(''):
            path.remove('')
        if not path:
            logging.error('bad query (empty query): %s' % url)
            return (None, None)

        for element in path:
            if (len(element) == 0) or not (element[0].isalnum() or element[0] == '_'):
                logging.error('bad query (invalid first char): %s' % url)
                return (None, None)
            if not check_sanity(element, accept_for_path):
                logging.error('bad query (invalid char): %s' % url)
                return (None, None)

        opts = dict()
        for key, value in parse_qsl(u.query):
            key, value = unquote(key), unquote(value)
            if not check_sanity(key, accept_for_key) or not check_sanity(value, accept_for_value):
                logging.error('bad query (invalid char): {"%s": "%s"} in %s' % (key, value, url))
                return (None, None)
            opts[key] = value
            
        return (path, opts)

        
    def make_reply(self, result, output=None, good_response=200):
        """create a Reply object from a result value that will be returned from self.process_XXX_request()
        Note:
          The result values are either (see sd_component.process_XXX()):
            - contents as Python dict, to reply as a JSON string with a "good" HTTP response (2xx)
            - content-type (MIME) as string, with reply contents written in output
            - HTTP response code as int
            - False for error (HTTP response 400 "Bad request")
            - None if the path is not the target (chain of responsibility)
        """
        if type(result) in [ dict, list ]:
            return Reply(good_response, 'application/json', json.dumps(result, **self.json_kwargs).encode())
        elif type(result) is int:
            return Reply(result)
        elif type(result) is str:
            if output is not None:
                return Reply(good_response, result, output.getvalue())
            else:
                return Reply(good_response, result, ''.encode())
        elif type(result) is bool:
            if result is True:
                result = {'status': 'ok'}
                return Reply(good_response, 'application/json', json.dumps(result, **self.json_kwargs).encode())
            else:
                logging.error('Bad request: %s' % url)
                return Reply(400)     # Bad Request
        else:
            logging.error('Bad URL: %s' % url)
            return Reply(400)       # Bad Request


    def process_get_request(self, url):
        """processes a GET request of the URL, and returns a Reply object
        """
        logging.debug(f'GET {url}')
        path, opts = self.parse_url(url)
        if path is None:
            return Reply(400)   # Bad Request

        with io.BytesIO() as output:
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
                    result = this_result
                    break

            return self.make_reply(result, output)

        return Reply(500)   # Internal Server Error


    def process_post_request(self, url, doc):
        """processes a POST request of the URL with content in doc, and returns a Reply object
        """
        logging.debug(f'POST {url}')
        path, opts = self.parse_url(url)
        if path is None:
            return Reply(400)   # Bad Request

        with io.BytesIO() as output:
            # Only first output is returned
            result = None
            for component in self.components:
                result = component.process_post(path, opts, doc, output)
                if result is not None:
                    break
                
            return self.make_reply(result, output, good_response=201)

        return Reply(500)   # Internal Server Error

    
            
    def process_delete_request(self, url):
        """processes a DELETE request of the URL with content in doc, and returns a Reply object
        """
        logging.debug(f'DELETE {url}')
        path, opts = self.parse_url(url)
        if path is None:
            return Reply(400)   # Bad Request

        # Only first delete is performed
        result = None
        for component in self.components:
            result = component.process_delete(path, opts)
            if result is not None:
                break

        return self.make_reply(result, good_response=200)
