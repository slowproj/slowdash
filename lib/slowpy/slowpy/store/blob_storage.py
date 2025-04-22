# Created by Sanshiro Enomoto on 21 April 2025 #

import sys, os, time, datetime
from string import Template
import hashlib, uuid


class BlobStorage:
    def write(self, blob: bytes, timestamp:int=None):
        pass



class BlobStorage_File(BlobStorage):
    def __init__(self, basepath:str='./blob', names=['%Y', '%m','%d-%H%M%S-%Z'], prefix='', ext=''):
        '''
        - File Location: os.path.join(basepath, names[:-1])
        - File Name: prefix + names[-1] + ext
        - Names can include template parameters:
             - %Y,%y,%m,%d,%H,%M,%S,%z,%Z: strftime parameters (using localtime with time-zone)
             - ${timestamp}: UNIX timestamp
             - ${uuid}: UUID
             - ${md5}: File MD5
        - After parameter substitution, only alphabets, digits, '_', '-', '+', and '.' are allowed for a name
        '''
        self.basepath = basepath
        self.names = names
        self.prefix = prefix
        self.ext = ext
        
        if len(self.names) < 1:
            logging.error('BlobStorage_File: name list too short')
            
    
    def write(self, blob:bytes, timestamp:int=None):
        now = int(timestamp if timestamp is not None else time.time())
        date = datetime.datetime.fromtimestamp(now).astimezone()
        params = {
            'timestamp': now,
            'uuid': uuid.uuid4(),
            'md5': hashlib.md5(blob).hexdigest(),
        }
        
        this_names = []
        for name in self.names:
            this_names.append(date.strftime(Template(name).safe_substitute(**params)))
        if len(this_names) < 1:
            return None
        
        dirname = os.path.join(self.basepath, *(this_names[:-1]))
        if len(dirname) > 0:
            if not os.path.isdir(dirname):
                try:
                    os.makedirs(dirname)
                except:
                    logging.error('BlobStorage_File.write(): unable to create directory: ' + dirname)
                    return None
            
        filename = self.prefix + this_names[-1] + self.ext
        filepath = os.path.join(dirname, filename)
        if len(filepath) == 0:
            logging.error('BlobStorage_File.write(): empty file path')
            return None
        try:
            with open(filepath, "wb") as f:
                f.write(blob)
        except Exception as e:
            logging.error(f'BlobStorage_File.write(): unable to write file: {filepath}: %s' % str(e))

        return filepath
        

    
if __name__ == '__main__':
    storage = BlobStorage_File(ext='.txt')
    filepath = storage.write(b'hello, this is a sample blob.\n')
    print(filepath)
