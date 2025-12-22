# Created by Sanshiro Enomoto on 24 April 2025 #

import os, logging


class BlobStorage:
    def __init__(self, app, project, params):
        pass
        
    async def get_blob(self, blob_id:str):
        """
        Returns: a tuple of (content_type:str, content:bytes)
        """
        return None, None


    
class BlobStorage_File(BlobStorage):
    def __init__(self, app, project, params):
        super().__init__(app, project, params)
        self.basedir = params.get('base_directory', 'data/blob')


    async def get_blob(self, blob_id:str):
        if not blob_id.startswith('file:'):
            return None, None

        filepath = blob_id[5:]
        for p in filepath.split(os.path.sep):
            if (
                (len(p) == 0) or p.startswith('.') or
                (not p.replace('_','').replace('-','').replace('+','').replace('.','').isalnum())
            ):
                logging.warning(f'get_blob(): invalid file path: {filepath}')
                return None, None
            
        filepath = os.path.join(self.basedir, filepath)
        if not os.path.exists(filepath):
            logging.warning(f'get_blob(): file not found: {filepath}')
            return None, None
        if not os.path.isfile(filepath):
            logging.warning(f'get_blob(): not a file: {filepath}')
            return None, None
        if not os.access(filepath, os.R_OK):
            logging.warning(f'get_blob(): permission denied: {filepath}')
            return None, None

        content = None
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
        except Exception as e:
            logging.warning(f'Slowlette_FileResponse: system error: {filepath}: {e}')
            return None, None

        ext = os.path.splitext(filepath)[1]
        if ext == '.html':
            content_type = 'text/html'
        elif ext == '.json':
            content_type = 'application/json'
        elif ext == '.yaml':
            content_type = 'application/yaml'
        elif ext == '.png':
            content_type = 'image/png'
        elif ext == '.svg':
            content_type = 'image/svg+xml'
        elif ext in ['.jpg', '.jpeg']:
            content_type = 'image/jpeg'
        elif ext == '.pdf':
            content_type = 'application/pdf'
        elif ext in ['.txt', '.py']:
            content_type = 'text/plain'
        else:
            content_type = 'application/octet-stream'
            
        return content_type, content

