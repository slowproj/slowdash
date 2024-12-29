
import time, datetime, json, uuid, re, logging
import component


class Export_Notebook(component.ComponentPlugin):
    def __init__(self, app, project, **params):
        super().__init__(app, project, **params)

        self.nbformat = 4
        self.nbformat_minor = 5

        
    def public_config(self):
        return {
            'notebook_format_version': f'{self.nbformat}.{self.nbformat_minor}'
        }

        
    def process_get(self, path, opts, output):
        if len(path) > 1 and path[1] == 'python':
            output.write(self.generate_python(path[1], opts).encode())
            return 'text/plain'
        
        elif len(path) > 1 and path[1] == 'notebook':
            notebook = self.generate_notebook(path[1], opts)
            output.write(json.dumps(notebook, indent=4).encode())
            return 'text/plain'

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

        if not slowdash_url.replace(':', '0').replace('/', '0').replace('.', '0').replace(':', '0').replace('~', '0').isalnum():
            slowdash_url = 'http://SLOW.DASH.URL.HERE'
            
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
        |#slowfetch.set_user(USER, PASS)           # set the password if the SlowDash page is protected
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
            'nbformat': self.nbformat,
            'nbformat_minor': self.nbformat_minor,
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
