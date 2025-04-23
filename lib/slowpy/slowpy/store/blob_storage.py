# Created by Sanshiro Enomoto on 21 April 2025 #

import sys, os, time, re, json, datetime, logging
from string import Template
import hashlib, uuid


class BlobStorage:
    def write(self, blob: bytes, timestamp:int=None, filename:str=None, mime=None):
        """stores the blob data, and returns a SlowDash blob entry
        """
        pass


    @staticmethod
    def _get_mime(ext):
        if ext == '.html':
            mime = 'text/html'
        elif ext == 'json':
            mime = 'application/json'
        elif ext == 'yaml':
            mime = 'application/yaml'
        elif ext == '.png':
            mime = 'image/png'
        elif ext == '.svg':
            mime = 'image/svg+xml'
        elif ext in ['.jpg', '.jpeg']:
            mime = 'image/jpeg'
        elif ext == '.pdf':
            mime = 'application/pdf'
        elif ext in ['.txt', '.py']:
            mime = 'text/plain'
        else:
            mime = None  # 'application/octet-stream'

        return mime


class BlobStorage_File(BlobStorage):
    def __init__(self, *, basedir='.', names=['blob', '%Y', '%m', '%y%m%d-%H%M%S-%Z'], prefix='', ext='', mime=None):
        """
        - The file location and name to be created depend on whether a file name is given in write() or not:
            - If file name is given:
                - File Location: os.path.join(basedir, names)
                - File Name: as speficied in filename parameter of write()
            - If file name is not given:
                - File Location: os.path.join(basedir, names[:-1])
                - File Name: prefix + names[-1] + ext
        - Names can include template parameters:
             - %Y,%y,%m,%d,%H,%M,%S,%z,%Z: strftime parameters (using localtime with time-zone)
             - ${timestamp}: UNIX timestamp
             - ${uuid}: UUID
             - ${md5}: File MD5
             - ${md5[N:M]}: File MD5 slice (e.g., ${md5[0:2]} for the first two hex digits)
        - After parameter substitution, only alphabets, digits, '_', '-', '+', and '.' are allowed for a name
        """
        
        self.basedir = basedir
        self.names = names
        self.prefix = prefix
        self.ext = ext
        self.mime = mime

        if len(self.ext) > 0:
            if not self.ext.startswith('.'):
                self.ext = '.' + self.ext
            if self.mime is None:
                self.mime = BlobStorage._get_mime(self.ext)
        
        if len(self.names) < 1:
            logging.error('BlobStorage_File: name list too short')
            
    
    def write(self, blob:bytes, timestamp:int=None, filename:str=None, mime:str=None):
        """
        Parameters:
            - blob (bytes): the data
            - timestamp (int): timestamp for filepath template substituion, None for "now"
            - filename: the name of the file to be created in the storage (optional: see __init__() description)
        Returns:
            - blob-id (file path excluding the basedir) on success
            - None on error
        """
        
        if (len(self.names) < 1) and (filename is None):
            logging.error(f'BlobStorage_File.write(): file name not provided')
            return None
        
        now = int(timestamp if timestamp is not None else time.time())
        date = datetime.datetime.fromtimestamp(now).astimezone()
        uuid4 = uuid.uuid4()
        md5 = hashlib.md5(blob).hexdigest()
        params = {
            'timestamp': now,
            'uuid': uuid4,
            'md5': md5,
        }

        this_names = []
        for name_k in self.names:
            this_name_k = date.strftime(Template(name_k).safe_substitute(**params))
            for N,M in re.findall(r'\$\{md5\[(\d+):(\d+)\]\}', name_k):
                this_name_k = this_name_k.replace('${md5[%s]}'%f'{N}:{M}', md5[int(N):int(M)])
                
            if not this_name_k.replace('_','').replace('-','').replace('+','').replace('.','').isalnum():
                logging.error(f'BlobStorage_File.write(): bad file name: {this_name_k}')
                return None
            this_names.append(this_name_k)

        mime = mime if mime is not None else self.mime
        if filename is not None:
            dirname = os.path.join(*this_names)
            if mime is None:
                mime = BlobStorage._get_mime(os.path.splitext(filepath)[1])
        else:
            dirname = os.path.join(*(this_names[:-1]))
            filename = self.prefix + this_names[-1] + self.ext
        if mime is None:
            mime = 'application/octet-stream'
            
        filepath = os.path.join(dirname, filename)
        if len(filepath) == 0:
            logging.error('BlobStorage_File.write(): empty file path')
            return None

        fulldir = os.path.join(self.basedir, dirname)
        if (len(fulldir) > 0) and not os.path.isdir(fulldir):
            try:
                os.makedirs(fulldir)
            except:
                logging.error('BlobStorage_File.write(): unable to create directory: ' + fulldir)
                return None

        fullpath = os.path.join(self.basedir, filepath)
        try:
            with open(fullpath, "wb") as f:
                f.write(blob)
        except Exception as e:
            logging.error(f'BlobStorage_File.write(): unable to write file: {fullpath}: %s' % str(e))

        return json.dumps({
            'mime': mime,
            'id': f'file:{filepath}'
        })
        

    
if __name__ == '__main__':
    storage = BlobStorage_File(names=['${md5[0:2]}-${md5[2:4]}', '${md5}'], ext='txt')
    filepath = storage.write(b'hello, this is a sample blob.\n')
    print(filepath)
