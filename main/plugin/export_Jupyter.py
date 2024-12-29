
import time, datetime, json, uuid, re, requests, logging
import export_Notebook


class Export_Jupyter(export_Notebook.Export_Notebook):
    def __init__(self, app, project, params):
        super().__init__(app, project, params)
        
        self.jupyter_url = params.get('url', '')
        self.jupyter_token = params.get('token', '')
        
        # in containers, URLs might be different from what external browsers see
        self.jupyter_internal_url = params.get('jupyter_internal_url', '').strip()
        self.slowdash_internal_url = params.get('slowdash_internal_url', '').strip()
        if len(self.jupyter_internal_url) == 0:
            self.jupyter_internal_url = self.jupyter_url
        if len(self.slowdash_internal_url) == 0:
            self.slowdash_internal_url = None
        
        self.jupyter_session = None
        self.xsrf_token = ''

        
    def public_config(self):
        config = super().public_config()
        config.update({
            "url": self.jupyter_url
        })
        return config

        
    def process_post(self, path, opts, doc, output):
        if len(path) > 2 and path[1] == 'jupyter':
            try:
                record = json.loads(doc.decode())
            except Exception as e:
                logging.error('Jupyter post: JSON decoding error: %s' % str(e))
                return 400 # Bad Request
            filename = record.get('filename', None)
            if filename is None or not filename.replace('_', '0').replace('-', '0').replace('.', '0').isalnum():
                return 400 # Bad Request

            if self.slowdash_internal_url is not None:
                opts['slowdash_url'] = self.slowdash_internal_url
            notebook = self.generate_notebook(path[2], opts)
            
            return self.post_notebook(filename, notebook, output)
        
        return None


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
