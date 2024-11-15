
import time, datetime, json, uuid, re, requests, logging
import extension


class Extension_Jupyter(extension.ExtensionModule):
    def __init__(self, project_config, module_config, slowdash):
        super().__init__(project_config, module_config, slowdash)
        self.jupyter_url = module_config.get('url', '')
        self.jupyter_token = module_config.get('token', '')
        self.jupyter_session = None
        self.xsrf_token = ''

        # in containers, URLs might be different from what external browsers see
        self.jupyter_internal_url = module_config.get('jupyter_internal_url', '').strip()
        self.slowdash_internal_url = module_config.get('slowdash_internal_url', '').strip()
        if len(self.jupyter_internal_url) == 0:
            self.jupyter_internal_url = self.jupyter_url
        if len(self.slowdash_internal_url) == 0:
            self.slowdash_internal_url = None
        
        self.public_config['url'] = self.jupyter_url

        
    def process_get(self, path, opts, output):
        if len(path) > 1 and path[0] == 'python':
            output.write(self.generate_python(path[1], opts).encode())
            return 'text/plain'
        elif len(path) > 1 and path[0] == 'notebook':
            notebook = self.generate_notebook(path[1], opts)
            output.write(json.dumps(notebook, indent=4).encode())
            return 'text/plain'

        return None

    
    def process_post(self, path, opts, doc, output):
        if len(path) > 1 and path[0] == 'jupyter':
            try:
                record = json.loads(doc.decode())
            except Exception as e:
                logging.error('Jupyter post: JSON decoding error: %s' % str(e))
                return 400 # Bad Request
            filename = record.get('filename', None)
            if filename is None or not filename.replace('_', '0').replace('-', '0').replace('.', '0').isalnum():
                return 400 # Bad Request
            notebook = self.generate_notebook(path[1], opts)
            return self.post_notebook(filename, notebook, output)
        
        return None

    
    def generate_cells(self, params, opts):
        try:
            channels = params.split(',')
            length = float(opts.get('length', '3600'))
            to = float(opts.get('to', int(time.time())+1))
            resample = float(opts.get('resample', -1))
            reducer = opts.get('reducer', None)
            filler = opts.get('filler', None)
            slowdash_url = opts.get('slowdash_url', '*')
            datatype = opts.get('datatype', 'timeseries')
        except Exception as e:
            logging.error(e)
            return None

        if self.slowdash_internal_url is not None:
            slowdash_url = self.slowdash_internal_url
        elif not slowdash_url.replace(':', '0').replace('/', '0').replace('.', '0').replace(':', '0').replace('~', '0').isalnum():
            slowdash_url = 'http://SLOW.DASH.URL.HERE:PORT'
            
        channels = []
        for ch in params.split(','):
            if ch.replace('_', '0').replace('-', '0').replace('.', '0').replace(',', '0').replace(':', '0').isalnum():
                channels.append(ch)
        start = datetime.datetime.fromtimestamp(to-length).astimezone().isoformat()
        stop = datetime.datetime.fromtimestamp(to).astimezone().isoformat()
        if resample < 0:
            resample = None
        if reducer not in [ 'last', 'mean', 'median' ]:
            reducer = None
        if filler not in [ 'fillna', 'last', 'linear' ]:
            filler = None

        cells = []
        cells.append(f'''
        |from slowpy import SlowFetch
        |slowfetch = SlowFetch({repr(slowdash_url)})
        |#sf.set_user(USER, PASS)                  # set the password if the SlowDash page is protected
        ''')
        cells.append(f'''
        |data = slowfetch.data(
        |    channels = {repr(channels)},
        |    start = {repr(start)},  # Date-time string, UNIX time, or negative integer for seconds to "stop"
        |    stop = {repr(stop)},   # Date-time string, UNIX time, or non-positive integer for seconds to "now"
        |    resample = {repr(resample)},                      # resampling time-backets intervals, zero for auto, None to disable
        |    reducer = {repr(reducer)},                       # 'last' (None), 'mean', 'median'
        |    filler = {repr(filler)},                        # 'fillna' (None), 'last', 'linear'   ### NOT IMPLEMENTED YET ###
        |)
        ''')
        if datatype == 'timeseries':
            cells.append(f'''
            |from matplotlib import pyplot as plt
            | 
            |for ch, (t, x) in data.items():
            |    plt.plot(t, x, label=ch)
            |plt.legend()
            ''')
        else:
            cells.append(f'''
            |# to plot histogram/graph, we use "slowpy.slowplot" instead of "matplotlib.pyplt"
            |from slowpy import slowplot as plt
            | 
            |# plot the last object in the time-series of objects
            |for ch, (t, x) in data.items():
            |    plt.plot(x[-1], label=ch)
            |plt.legend()
            ''')

        return [ re.sub('^[ ]*\\|', '', cell.strip() + '\n', flags=re.MULTILINE) for cell in cells ]


    def generate_python(self, params, opts):
        cells = self.generate_cells(params, opts)  + [ 'plt.show()' ]
        return '\n'.join([ '#%%\n' + cell for cell in cells])

    
    def generate_notebook(self, params, opts):
        notebook = {
            'nbformat': 4,
            'nbformat_minor': 5,
            'metadata': {
                'language_info': {
                    'name': 'python',
                    'file_extension': '.py',
                    'mimetype': 'text/x-python'
                },
                'kernelspec': {
                    'name': 'python3',
                    'language': 'python',
                    'display_name': 'Python 3 (ipykernel)'
                }
            },
            'cells': []
        }
                
        for src in self.generate_cells(params, opts):
            cell = {
                'cell_type': 'code',
                'id': str(uuid.uuid4()),
                'metadata': {},
                'execution_count': None,
                'outputs': [],
                'source': [ '%s\n' % line for line in src.split('\n') ][:-1]
            }
            notebook['cells'].append(cell)

        return notebook


    def connect_jupyter(self):
        if self.jupyter_session is not None:
            return True
        if len(self.jupyter_internal_url) == 0:
            return False
        
        try:
            self.jupyter_session = requests.Session()
            resonse = self.jupyter_session.get(f'{self.jupyter_internal_url}/tree')
            self.xsrf_token = self.jupyter_session.cookies.get('_xsrf')
        except Exception as e:
            logging.error('Jupyter connection: %s' % str(e))
            self.jupyter_session = None
            return False

        return True
            
            
    def post_notebook(self, filename, notebook, output):
        if not self.connect_jupyter():
            return { 'status': 'error', 'message': 'unable to connect to Jupyter' }

        try:
            response = self.jupyter_session.put(
                f'{self.jupyter_internal_url}/api/contents/{filename}',
                headers = {
                    'Content-Type': 'application/json',
                    'X-XSRFToken': self.xsrf_token,
                    'Authorization':f'Token {self.jupyter_token}'
                },
                data = json.dumps({
                    'type': 'notebook',
                    'format': 'json',
                    'content': notebook
                })
            )
            if response.status_code in [ 200, 201 ]:
                return { 'status': 'ok', 'notebook_url': f'{self.jupyter_url}/notebooks/{filename}' }
            else:
                logging.error('Jupyter Notebook posting: %d %s' % (response.status_code, response.text))
                return { 'status': 'error', 'message': response.text }
            
        except Exception as e:
            logging.error('Jupyter Notebook posting: %s' % str(e))
            return { 'status': 'error', 'message': str(e) }
