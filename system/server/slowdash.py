#! /usr/bin/env python3
# Created by Sanshiro Enomoto on 3 Sep 2021 #


import sys, os, stat, pwd, grp, io, time, glob, json, yaml, logging
import datasource, usermodule
from slowdash_config import Config


class App:
    def __init__(self, project_dir=None, is_cgi=False):
        self.config = Config(project_dir)
        self.project = self.config.project
        self.project_dir = self.config.project_dir
        self.datasource_list = []
        self.usermodule_list = []
        self.error_message = ''

        if self.project is None:
            self.datasource_list = [ datasource.DataSource({}, self.config) ]
            return

        ### Load Datasources ###
        
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
                datasource_module = datasource.load(ds_type, self.config, params)
                if datasource_module is None:
                    self.error_message = 'Unable to load data source: %s' % ds_type
                    logging.error(self.error_message)
                else:
                    self.datasource_list.append(datasource_module)

        ### Load User Module ###
        
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
            module = usermodule.load(filepath, self.config, params)
            if module is None:
                self.error_message = 'Unable to load user module: %s' % filepath
                logging.error(self.error_message)
            else:
                self.usermodule_list.append(module)


    def __del__(self):
        self.usermodule_list.clear()
        
        
    def get(self, params, opts, output):
        if self.project is None:
            output.write(json.dumps({}).encode())
            return 'application/json'

        content_type = 'application/json'
        
        if params[0] == 'config':
            if len(params) <= 2:
                self.config.update()
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
                    'style': self.config.project.get('style', None),
                }
                
                if (len(params) == 2) and (params[1] == 'list'):
                    contents = { 'slowdash': [], 'slowplot': [] }
                    filelist = []
                    for filepath in glob.glob(os.path.join(self.project_dir, 'config', '*-*.*')):
                        filelist.append([filepath, int(os.path.getmtime(filepath))])
                    filelist = sorted(filelist, key=lambda entry: entry[1], reverse=True)
                    for filepath, mtime in filelist:
                        rootname, ext = os.path.splitext(os.path.basename(filepath))
                        kind, name = rootname.split('-', 1)
                        if ext not in [ '.json', '.yaml', '.html' ]:
                            continue
                        if kind not in contents:
                            contents[kind] = []

                        meta_info, config_error = {}, None
                        if ext in [ '.json', '.yaml' ]:
                            with open(filepath) as f:
                                try:
                                    this_config = yaml.safe_load(f)
                                    meta_info = this_config.get('meta', {})
                                except Exception as e:
                                    config_error = str(e)
                                    logging.error('Invalid Configuration File: %s' % str(e))
                    
                        contents[kind].append({
                            'name': name,
                            'mtime': mtime,
                            'title': meta_info.get('title', ''),
                            'description': meta_info.get('description', ''),
                            'config_file': rootname + ext,
                            'config_error': config_error
                        })
                    doc['contents'] = contents

                elif (len(params) == 2) and (params[1] == 'filelist'):
                    doc, filelist = [], []
                    for filepath in glob.glob(os.path.join(self.project_dir, 'config', '*')):
                        filelist.append([filepath, int(os.path.getmtime(filepath))])
                    filelist = sorted(filelist, key=lambda entry: entry[0], reverse=False)
                    for filepath, mtime in filelist:
                        filestat = os.lstat(filepath)
                        doc.append({
                            'name': os.path.basename(filepath),
                            'size': os.path.getsize(filepath),
                            'mode': stat.filemode(filestat.st_mode),
                            'owner': pwd.getpwuid(filestat.st_uid)[0],
                            'group': grp.getgrgid(filestat.st_gid)[0],
                            'mtime': mtime
                        })
                    
                output.write(json.dumps(doc, indent=4).encode())
                return content_type
                    
            elif (len(params) == 3) and (params[1] == 'file'):
                filepath = os.path.join(self.project_dir, 'config', params[2])
                if not (os.path.isfile(filepath) and os.access(filepath, os.R_OK)):
                    return None

                ext = os.path.splitext(filepath)[1].lower()
                if ext == '':
                    ext = '.yaml'
                    
                output.flush()
                
                if ext in [ '.json', '.yaml' ]:
                    if opts.get('content', None) == 'raw':
                        content_type = 'plain/text'
                        content_file = io.FileIO(filepath, 'r')
                        output.write(content_file.readall())
                    else:
                        meta = {
                            'type': 'config',
                            'name': params[2],
                            'error': None
                        }
                        try:
                            with open(filepath) as f:
                                doc = yaml.safe_load(f)
                        except yaml.YAMLError as e:
                            if hasattr(e, 'problem_mark'):
                                line = e.problem_mark.line+1
                                meta['error'] = 'Line %d: %s' % (line, e.problem)
                                meta['error_line'] = line
                            else:
                                meta['error'] = str(e)
                            if opts.get('content', None) != 'meta':
                                return None
                        if opts.get('content', None) == 'meta':
                            content_type = 'application/json'
                            output.write(json.dumps(meta, indent=4).encode())
                        else:
                            content_type = 'application/json'
                            output.write(json.dumps(doc, indent=4).encode())
                            
                elif ext in [ '.png', '.jpg', '.jpeg', '.svg', '.html', '.csv' ]:
                    if ext == '.svg':
                        content_type = 'image/svg+xml'
                    elif ext == '.png':
                        content_type = 'image/png'
                    elif ext in ['.jpg', '.jpeg']:
                        content_type = 'image/jpeg'
                    elif ext == '.html':
                        content_type = 'text/html'
                    elif ext == '.csv':
                        content_type = 'text/csv'
                    content_file = io.FileIO(filepath, 'r')
                    output.write(content_file.readall())
                    
                else:
                    return None
                return content_type
            else:
                return None
                
        result = None
        if params[0] == 'channels':
            result = []
            for ds in self.datasource_list:
                channels = ds.get_channels()
                if channels is not None:
                    result.extend(channels)
            for usermodule in self.usermodule_list:
                channels = usermodule.get_channels()
                if channels is not None:
                    result.extend(channels)
                
        elif params[0] in ['data'] and len(params) >= 2:
            result = {}
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
                
            for ds in self.datasource_list:
                result_ts = ds.get_timeseries(channels, length, to, resample, reducer)
                if result_ts is not None:
                    result.update(result_ts)
                result_obj = ds.get_object(channels, length, to)
                if result_obj is not None:
                    result.update(result_obj)
                    
            for usermodule in self.usermodule_list:
                for ch in channels:
                    data = usermodule.get_data(ch)
                    if data is None:
                        continue
                    result[ch] = {
                        'start': to-length, 'length': length,
                        't': to,
                        'x': data
                    }
            
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
        if self.project is None:
            return 404

        if path_list[0] == 'config':
            if (len(path_list) < 3) or (path_list[1] != 'file'):
                return 403
            filename = path_list[2]
            if not filename.replace('_', '').replace('-', '').replace('.', '').isalnum():
                return 403
            if filename.split('-', 1)[0] not in [ 'slowdash', 'slowplot', 'slowcruise' ]:
                return 403
            if os.path.splitext(filename)[1] not in [ '.json', '.yaml' ]:
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

            
        elif path_list[0] == 'control':
            try:
                json_doc = json.loads(doc.decode())
                logging.info("DISPATCH: %s" % json_doc)
            except Exception as e:
                logging.error('Dispatch: JSON decoding error: %s' % str(e))
                return 400

            # user code might write something to stdout, which can disturb HTTP response
            stdout = sys.stdout
            sys.stdout = io.StringIO()
            result = None
            for usermodule in self.usermodule_list:
                result = usermodule.process_command(json_doc)
                if result is not None:
                    # chain of responsibility
                    break
            sys.stdout.close()
            sys.stdout = stdout
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
            
        else:
            return 400

        return 201

    
    
from urllib.parse import urlparse, parse_qsl
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
        string = string.replace('_', '').replace('-', '').replace('.', '').replace(',', '')
        string = string.replace(':', '').replace('[', '').replace(']', '')
        return string.isalnum()
        
    def process_get_request(self, url):
        if self.app is None:
            return Reply(404)
        u = urlparse(url)
        path_list = u.path.split('/')
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
        path_list = u.path.split('/')
        while path_list.count(''):
            path_list.remove('')
        for element in path_list:
            if (len(element) == 0) or not element[0].isalpha():
                logging.error('bad file name (invalid first char): %s' % url)
                return Reply(400)
            if not element.replace('_', '').replace('-', '').replace('.', '').isalnum():
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
