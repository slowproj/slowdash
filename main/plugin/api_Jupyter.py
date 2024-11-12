
import time, datetime, json, uuid, re, requests, logging
import extension


class Extension_Jupyter(extension.ExtensionModule):
    def __init__(self, project_config, module_config, slowdash):
        self.jupyter_url = module_config.get('url', 'http://localhost:8888')
        self.jupyter_token = module_config.get('token', '')
        self.jupyter_session = None
        self.xsrf_token = ''


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
            notebook = self.generate_notebook(path[1], opts)
            return self.post_notebook(notebook, output)
        
        return None

    
    def generate_cells(self, params, opts):
        try:
            channels = params.split(',')
            length = float(opts.get('length', '3600'))
            to = float(opts.get('to', int(time.time())+1))
            resample = float(opts.get('resample', -1))
            reducer = opts.get('reducer', 'last')
            filler = opts.get('filler', None)
        except Exception as e:
            logging.error(e)
            return None
        if resample < 0:
            resample = None

        cells = []
        cells.append(f'''
        |from slowpy import SlowFetch
        |from matplotlib import pyplot as plt
        | 
        |sf = SlowFetch('http://localhost:18881')
        |#sf.set_user(USER, PASS)                  # set the password if the SlowDash page is protected
        ''')
        cells.append(f'''
        |df = sf.dataframe(                        ### this returns a Pandas DataFrame
        |    channels = ['ch0','ch1','ch2'],           
        |    start = '2024-11-02T19:36:24-07:00',  # Date-time string, UNIX time, or negative integer for seconds to "stop"
        |    stop = '2024-11-02T19:36:24-07:00',   # Date-time string, UNIX time, or non-positive integer for seconds to "now"
        |    resample = 0,                         # resampling time-backets intervals, zero for auto
        |    reducer = 'mean',                     # 'last' (None), 'mean', 'median'
        |    filler = None)                        # 'fillna' (None), 'last', 'linear'
        ''')
        cells.append(f'''
        |df.plot(x='DateTime', y=['ch0','ch1','ch2'])
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
        
        try:
            self.jupyter_session = requests.Session()
            resonse = self.jupyter_session.get(f'{self.jupyter_url}/tree')
            self.xsrf_token = self.jupyter_session.cookies.get('_xsrf')
        except Exception as e:
            logging.error('Jupyter connection: %s' % str(e))
            self.jupyter_session = None
            return False

        return True
            
            
    def post_notebook(self, notebook, output):
        if not self.connect_jupyter():
            return { 'status': 'error', 'message': 'unable to connect to Jupyter' }

        filename = 'SlowPlot-' + datetime.datetime.now().strftime('%y%m%d-%H%M%S') + ".ipynb";
        try:
            response = self.jupyter_session.put(
                f'{self.jupyter_url}/api/contents/{filename}',
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
