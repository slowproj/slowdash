#! /usr/bin/env python3
# Created by Sanshiro Enomoto on 3 Sep 2021 #


import sys, os, stat, pwd, grp, io, time, glob, json, yaml, logging
import datasource, usermodule, taskmodule
from slowdash_config import Config


class App:
    def __init__(self, project_dir=None, is_cgi=False):
        self.config = Config(project_dir)
        self.project = self.config.project
        self.project_dir = self.config.project_dir
        self.datasource_list = []
        self.usermodule_list = []
        self.taskmodule_list = []
        self.error_message = ''

        if self.project is None:
            self.datasource_list = [ datasource.DataSource({}, self.config) ]
            return

        ### Datasources ###
        
        datasource_node = self.project.get('data_source', None)
        if datasource_node is None:
            self.error_message = 'Data Source not defined'
            logging.warning(self.error_message)
            datasource_node = []
        elif not isinstance(datasource_node, list):
            datasource_node = [ datasource_node ]

        for node in datasource_node:
            url = node.get('url', '')
            ds_type = datasource.Schema.parse_dburl(url).get('type', None)
            ds_type = node.get('type', ds_type)
            params = node.get('parameters', {})
            if 'url' not in params:
                params['url'] = url
            if ds_type is None or len(ds_type) == 0:
                self.error_message = 'no datasource type specified'
                logging.error(self.error_message)
            else:
                datasource_plugin = datasource.load(ds_type, self.config, params)
                if datasource_plugin is None:
                    self.error_message = 'Unable to load data source: %s' % ds_type
                    logging.error(self.error_message)
                else:
                    self.datasource_list.append(datasource_plugin)

        ### User Modules ###
        
        usermodule_node = self.project.get('module', [])
        if not isinstance(usermodule_node, list):
            usermodule_node = [ usermodule_node ]
            
        for node in usermodule_node:
            if not isinstance(node, dict) or 'file' not in node:
                self.error_message = 'bad user module configuration'
                logging.error(self.error_message)
                continue
            if is_cgi and node.get('cgi_enabled', False) != True:
                continue
            filepath = node['file']
            params = node.get('parameters', {})
            module = usermodule.load(usermodule.UserModule, filepath, filepath, params)
            if module is None:
                self.error_message = 'Unable to load user module: %s' % filepath
                logging.error(self.error_message)
            else:
                self.usermodule_list.append(module)


        ### Task Modules ###
        
        taskmodule_node = self.project.get('task', [])
        if not isinstance(taskmodule_node, list):
            taskmodule_node = [ taskmodule_node ]
            
        for node in taskmodule_node:
            if not isinstance(node, dict):
                self.error_message = 'bad control module configuration'
                logging.error(self.error_message)
                continue
            if is_cgi and node.get('cgi_enabled', False) != True:
                continue
            if 'name' not in node:
                self.error_message = 'name is required for control module'
                logging.error(self.error_message)
                continue

            name = node['name']
            filepath = node.get('file', './config/slowtask-%s.py' % name)
            params = node.get('parameters', {})
            module = usermodule.load(taskmodule.TaskModule, filepath, name, params)
            if module is None:
                self.error_message = 'Unable to load control module: %s' % filepath
                logging.error(self.error_message)
            else:
                module.name = name
                self.taskmodule_list.append(module)


    def __del__(self):
        self.usermodule_list.clear()
        self.taskmodule_list.clear()
        
        
    def get(self, params, opts, output):
        content_type = 'application/json'
        result = None
        
        if (len(params) == 3) and (params[0] == 'config') and (params[1] == 'file'):
            return self._get_config_file(params[2], output)
            
        elif params[0] == 'config':
            if len(params) == 1:
                result = self._get_config(with_list=False)
            elif len(params) == 2:
                if params[1] == 'list':
                    result = self._get_config(with_list=True,with_content_meta=True)
                elif params[1] == 'filelist':
                    result = self._get_config_filelist()
            elif (len(params) == 3) and (params[1] == 'filemeta'):
                    result = self._get_config_filemeta(params[2])
                
        elif params[0] == 'channels':
            result = self._get_channels()
                
        elif params[0] in ['data'] and len(params) >= 2:
            try:
                channels = params[1].split(',')
                length = float(opts.get('length', '3600'))
                to = float(opts.get('to', int(time.time())))
                resample = float(opts.get('resample', -1))
                reducer = opts.get('reducer', 'last')
            except Exception as e:
                logging.error(e)
                return None
            if resample < 0:
                resample = None
            result = self._get_data(channels, length, to, resample, reducer)
            
        elif params[0] in ['blob'] and len(params) >= 3:
            for ds in self.datasource_list:
                mime_type = ds.get_blob(params[1], params[2:], output=output)
                if mime_type is not None:
                    return mime_type
            
        elif params[0] == 'dataframe' and len(params) >= 2:
            try:
                channels = params[1].split(',')
                length = float(opts.get('length', '3600'))
                to = float(opts.get('to', int(time.time())))
                resample = float(opts.get('resample', -1))
                reducer = opts.get('reducer', 'last')
                timezone = opts.get('timezone', 'local')
            except Exception as e:
                logging.error(e)
                return None
            if resample < 0:
                resample = None
            for ds in self.datasource_list:
                result = ds.get_dataframe(channels, length, to, resample, reducer, timezone)
                break ##....

        elif params[0] == 'authkey' and len(params) >= 2:
            name = params[1]
            word = opts.get('password', '')
            try:
                import bcrypt
            except:
                logging.error('install python module "bcrypt"')
                return None
            key = bcrypt.hashpw(word.encode("utf-8"), bcrypt.gensalt(rounds=12, prefix=b"2a")).decode("utf-8")
            result = { 'type': 'Basic', 'key':  '%s:%s' % (name, key) }
            
        if result is None:
            return None
        
        if params[0] == 'dataframe':
            content_type = 'text/csv'
            if type(result) is str:
                output.write(result.encode())
            else:
                output.write('\n'.join([
                    ','.join(['NaN' if col is None else col for col in row]) for row in result
                ]).encode())
        else:
            if type(result) is str:
                output.write(result.encode())
            else:
                output.write(json.dumps(result).encode())
            
        return content_type


    def post(self, path_list, opts, doc, output):
        if path_list[0] == 'config':
            if (len(path_list) < 3) or (path_list[1] != 'file'):
                return 403  # Forbidden
            else:
                return self._save_config_file(path_list[2], doc, opts)
        elif path_list[0] == 'control':
            return self._dispatch_control(doc, opts, output)
        
        return 400  # Bad Request

    
    def delete(self, path_list):
        if (len(path_list) < 3) or (path_list[1] != 'file'):
            return 403  # Forbidden
        
        filename = path_list[2]
        if (self.project_dir is None):
            return 404  # Not Found
        try:
            os.remove(os.path.join('config', filename))
        except Exception as e:
            logging.error('file deletion error: %s' % str(e))
            return 500
        return 200
        

    def _get_config(self, with_list=True, with_content_meta=True):
        self.config.update()
        if self.project is None:
            doc = {
                'project': {}
            }
        else:
            doc = {
                'project': {
                    'name': self.config.project.get('name', 'Untitled Project'),
                    'title': self.config.project.get('title', ''),
                    'error_message': self.error_message
                },
                'data_source_module': [
                    ds.modulename for ds in self.datasource_list
                ],
                'user_module': [
                    module.filepath for module in self.usermodule_list
                ],
                'control_module': [
                    module.filepath for module in self.taskmodule_list
                ],
                'style': self.config.project.get('style', None)
            }
            
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
                meta_info = self._get_config_filemeta(filename)

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

                
    def _get_config_filemeta(self, filename):
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
                    meta_info = this_config.get('meta', {})
            except yaml.YAMLError as e:
                if hasattr(e, 'problem_mark'):
                    line = e.problem_mark.line+1
                    meta_info['config_error_line'] = line
                    meta_info['config_error'] = 'Line %d: %s' % (line, e.problem)
                else:
                    meta_info['config_error'] = str(e)

        return meta_info
                    

    def _get_config_filelist(self):
        if self.project_dir is None:
            return []
        
        filelist = []
        for filepath in glob.glob(os.path.join(self.project_dir, 'config', '*-*.*')):
            filelist.append([filepath, int(os.path.getmtime(filepath))])
            filelist = sorted(filelist, key=lambda entry: entry[1], reverse=True)
                
        result = []
        for filepath, mtime in filelist:
            filestat = os.lstat(filepath)
            result.append({
                'name': os.path.basename(filepath),
                'size': os.path.getsize(filepath),
                'mode': stat.filemode(filestat.st_mode),
                'owner': pwd.getpwuid(filestat.st_uid)[0],
                'group': grp.getgrgid(filestat.st_gid)[0],
                'mtime': mtime
            })
            
        return result


    def _get_config_file(self, filename, output):
        if self.project_dir is None:
            return None
        filepath = os.path.join(self.project_dir, 'config', filename)
        if not (os.path.isfile(filepath) and os.access(filepath, os.R_OK)):
            return None
        
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
        else:
            return None
            
        output.flush()        
        if os.path.getsize(filepath) > 0:
            output.write(io.FileIO(filepath, 'r').readall())

        return content_type


    def _save_config_file(self, filename, doc, opts):
        if self.project_dir is None:
            return 500
        if (len(filename) == 0) or not filename[0].isalpha():
            return 403
        if not filename.replace('_', '0').replace('-', '0').replace('.', '0').replace(' ', '0').isalnum():
            return 403
        ext = os.path.splitext(filename)[1]
        if ext not in [ '.json', '.yaml', '.html', '.csv', '.svn', '.png', '.jpg', '.jpeg' ]:
            return 403

        config_dir = os.path.join(self.project_dir, 'config')
        if not os.path.isdir(config_dir):
            try:
                os.makedirs(config_dir)
            except:
                logging.error('unable to create directory: ' + config_dir)
                return 500
            
        mode = self.project.get('system', {}).get('file_mode', 0o644) + 0o100
        if mode & 0o070 != 0:
            mode = mode + 0o010
        if mode & 0o007 != 0:
            mode = mode + 0o001
        try:
            os.chmod(config_dir, mode)
        except Exception as e:
            logging.warn('unable to change file mode (%03o): %s: %s' % (mode, config_dir, str(e)))
            
        gid = self.project.get('system', {}).get('file_gid', -1)
        try:
            os.chown(config_dir, -1, gid)
        except Exception as e:
            logging.warn('unable to change file gid (%d): %s: %s' % (gid, config_dir, str(e)))

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
            logging.error(e)
            return 500    # Internal Server Error

        try:
            mode = self.project.get('system', {}).get('file_mode', 0o644)
            os.chmod(filepath, mode)
        except Exception as e:                
            logging.warn('unable to change file mode (%03o): %s: %s' % (mode, filepath, str(e)))
        try:
            gid = self.project.get('system', {}).get('file_gid', -1)
            os.chown(filepath, -1, gid)
        except Exception as e:
            logging.warn('unable to change file gid (%d): %s: %s' % (gid, config_dir, str(e)))

        return 201 # Created
    
                
    def _get_channels(self):
        result = []
        for src_list in [ self.datasource_list, self.usermodule_list, self.taskmodule_list ]:
            for src in src_list:
                channels = src.get_channels()
                if channels is not None:
                    result.extend(channels)

        return result

    
    def _get_data(self, channels, length, to, resample, reducer):
        result = {}
        for ds in self.datasource_list:
            result_ts = ds.get_timeseries(channels, length, to, resample, reducer)
            if result_ts is not None:
                result.update(result_ts)
            result_obj = ds.get_object(channels, length, to)
            if result_obj is not None:
                result.update(result_obj)
                    
        for module_list in [ self.usermodule_list, self.taskmodule_list ]:
            for module in module_list:
                for ch in channels:
                    data = module.get_data(ch)
                    if data is None:
                        continue
                    result[ch] = {
                        'start': to-length, 'length': length,
                        't': to,
                        'x': data
                    }

        return result

    
    def _dispatch_control(self, doc, opts, output):
        try:
            json_doc = json.loads(doc.decode())
            logging.info("DISPATCH: %s" % json_doc)
        except Exception as e:
            logging.error('Dispatch: JSON decoding error: %s' % str(e))
            return 400

        result = self._dispatch_task(json_doc)
        if result is None:
            result = self._dispatch_user_command(json_doc, opts, output)
        
        if result is None:
            return 400
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
                return 500

        return 'application/json'

        
    
    def _dispatch_task(self, doc):
        # user code might write something to stdout, which can disturb HTTP response
        stdout = sys.stdout
        sys.stdout = io.StringIO()
        result = None
        for module in self.taskmodule_list:
            result = module.process_command(doc)
            if result is not None:
                # chain of responsibility
                break
        sys.stdout.close()
        sys.stdout = stdout

        return result

    
    def _dispatch_user_command(self, doc, opts, output):
        # user code might write something to stdout, which can disturb HTTP response
        stdout = sys.stdout
        sys.stdout = io.StringIO()
        result = None
        for module in self.usermodule_list:
            result = module.process_command(doc)
            if result is not None:
                # chain of responsibility
                break
        sys.stdout.close()
        sys.stdout = stdout

        return result

    
        
    
from urllib.parse import urlparse, parse_qsl, unquote
import io

class Reply:
    def __init__(self, response, content_type=None, content=None):
        self.response = response
        self.content_type = content_type
        self.content = content
        self.content_readable = None

    def write_to(self, output):
        try:
            if self.content:
                if type(self.content) is str:
                    output.write(self.content.encode())
                else:
                    output.write(self.content)

            elif self.content_readable is not None:
                while True:
                    content = self.content_readable.read(1024*1024)
                    if content:
                        output.write(content)
                    else:
                        break
                    
        except Exception as e:
            logging.warn('error on sending out a reply: %s' % str(e))

        return self
        
    def destroy(self):
        if self.content_readable:
            content_readable.close()
            

            
class WebUI:
    def __init__(self, project_dir=None, is_cgi=False):
        self.app = App(project_dir, is_cgi)
        self.auth_list = self.app.config.auth_list

        
    def close(self):
        del self.app
        self.app = None

        
    def check_sanity(self, string):
        string = string.replace('_', '0').replace('-', '0').replace('.', '0').replace(',', '0').replace(' ', '0')
        string = string.replace(':', '0').replace('[', '0').replace(']', '0')
        return string.isalnum()

    
    def process_get_request(self, url):
        if self.app is None:
            return Reply(404)
        u = urlparse(url)
        path_list = unquote(u.path).split('/')
        while path_list.count(''):
            path_list.remove('')
        if not path_list:
            logging.error('bad query (empty query): %s' % url)
            return Reply(400)

        opts = dict()
        for key, value in parse_qsl(u.query):
            if not self.check_sanity(key + value):
                logging.error('bad query (invalid char): %s' % url)
                return Reply(400)
            opts[key] = value
            
        if path_list[0] == 'ping':            
            result = 'pong'
            return Reply(200, 'application/json', json.dumps(result, indent=4))
        if path_list[0] == 'echo':
            result = {'URL': url, 'Path': path_list[1:], 'Opts': opts}
            return Reply(200, 'application/json', json.dumps(result, indent=4))

        for element in path_list:
            if (len(element) == 0) or (not element[0].isalnum() and element[0] not in ['_']):
                logging.error('bad query (invalid first char): %s' % url)
                return Reply(400)
            if not self.check_sanity(element):
                logging.error('bad query (invalid char): %s' % url)
                return Reply(400)

        with io.BytesIO() as output:
            content_type = self.app.get(path_list, opts, output=output)

            if content_type is None:
                logging.error('API error: %s' % url)
                return Reply(503)

            return Reply(200, content_type, output.getvalue())


    def process_post_request(self, url, doc):
        if self.app is None:
            return Reply(404)
        u = urlparse(url)
        path_list = unquote(u.path).split('/')
        while path_list.count(''):
            path_list.remove('')
        for element in path_list:
            if (len(element) == 0) or not element[0].isalpha():
                logging.error('bad file name (invalid first char): %s' % url)
                return Reply(400)
            if not element.replace('_', '0').replace('-', '0').replace('.', '0').replace(' ', '0').isalnum():
                logging.error('bad file name (invalid char): %s' % url)
                return Reply(400)
        
        opts = dict()
        for key, value in parse_qsl(u.query):
            if not self.check_sanity(key + value):
                logging.error('bad query (invalid char): %s' % url)
                return Reply(400)
            opts[key] = value
            
        with io.BytesIO() as output:
            result = self.app.post(path_list, opts, doc, output=output)
            if type(result) is int:
                return Reply(result)
            elif type(result) is str:
                return Reply(201, result, output.getvalue())
            else:
                logging.error('API error: %s' % url)
                return Reply(500)

            
    def process_delete_request(self, url):
        if self.app is None:
            return Reply(404)
        u = urlparse(url)
        path_list = unquote(u.path).split('/')
        while path_list.count(''):
            path_list.remove('')
        for element in path_list:
            if (len(element) == 0) or not element[0].isalpha():
                logging.error('bad file name (invalid first char): %s' % url)
                return Reply(400)
            if not element.replace('_', '0').replace('-', '0').replace('.', '0').replace(' ', '0').isalnum():
                logging.error('bad file name (invalid char): %s' % url)
                return Reply(400)
        
        result = self.app.delete(path_list)
        if type(result) is int:
            return Reply(result)
        else:
            logging.error('API error: %s' % url)
            return Reply(500)
            
            

    
import slowdash_server

from optparse import OptionParser

usage = '''
  Web-Server Mode:    %prog [Options] --port=PORT
  Command-line Mode:  %prog [Options] Command'''


if __name__ == '__main__':
    optionparser = OptionParser(usage=usage)
    optionparser.add_option(
        '-p', '--port',
        action='store', dest='port', type='int', default=0,
        help='port number for web connection; command-line mode without this option'
    )
    optionparser.add_option(
        '--project-dir',
        action='store', dest='project_dir', type='string', default=None,
        help='project directory (default: current dir if not specified by SLOWDASH_PROJECT environmental variable)'
    )
    optionparser.add_option(
        '--logging',
        action='store', dest='loglevel', type='string', default='info',
        help='set log level. One of "debug", "info" (default)", "warn", or "error"'
    )
    (options, args) = optionparser.parse_args()

    if (len(args) < 1) and (options.port <= 0):
        optionparser.print_help()
        sys.exit(-1)

    logging.basicConfig(level=10)
        
    webui = WebUI(options.project_dir)

    if options.port <= 0:
        result = webui.process_get_request(args[0])
        result.write_to(sys.stdout.buffer).destroy()
        sys.stdout.write('\n')
        webui.close()
    else:
        index_file = 'slowhome.html'
        if webui.app.project is None:
            index_file = 'welcome.html'
        cgi_name = 'slowdash.cgi'
        sys_dir = os.path.dirname(os.path.abspath(os.path.join(__file__, os.pardir)))
        web_path = os.path.join(sys_dir, 'web')
        slowdash_server.start(options.port, webui, cgi_name, web_path, index_file)
