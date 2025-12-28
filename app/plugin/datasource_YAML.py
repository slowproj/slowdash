# Created by Sanshiro Enomoto on 18 October 2022 #


import sys, os, time, logging, yaml
from sd_datasource import DataSource

    
class DataSource_YAML(DataSource):
    def __init__(self, app, project, params):
        super().__init__(app, project, params)
        self.filepath = params.get('file', None)
        self.name = params.get('name', None)
        self.tree = None
        
        if self.filepath is None:
            logging.error('YAML file not specified')
            return
        if self.name is None:
            self.name = os.path.splitext(os.path.basename(self.filepath))[0]
        if not os.access(self.filepath, os.R_OK):
            logging.error('YAML file not readable: %s' % self.filepath)
            
        self.mtime = 0
        
        
    def get_channels(self):
        self._read_file()
            
        if self.tree is None:
            return []
        else:
            return [ { 'name': self.name, 'type': 'tree' } ]

    
    def get_timeseries(self, channels, length, to, resampling=None, reducer='last', filler='fillna', envelope=0):
        return {}

    
    def get_object(self, channels, length, to):
        result = {}
        
        self._read_file()
        if self.name in channels:
            result[self.name] = {
                'start': to-length, 'length': length,
                't': to,
                'x': {
                    'tree': self.tree
                }
            }
        
        return result

    
    def _read_file(self):
        if self.filepath is None:
            return

        # reload only if the file has been modified
        try:
            mtime = os.path.getmtime(self.filepath)
        except Exception as e:
            # file might have been removed
            self.mtime = 0
            self.tree = None
            return
        if mtime <= self.mtime:
            return
        self.mtime = mtime
        
        try:
            with open(self.filepath) as f:
                self.tree = yaml.safe_load(f)
        except Exception as e:
            logging.error('unable to read YAML file: %s, %s' % (self.filepath, str(e)))
            self.mtime = 0
            self.tree = None
        
