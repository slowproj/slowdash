# Created by Sanshiro Enomoto on 31 December 2024 #

import sys, os, logging
from sd_component import Component


class MiscApiComponent(Component):
    def __init__(self, app, project):
        super().__init__(app, project)

        
    def process_get(self, path, opts, output):
        if len(path) < 1:
            return None
        
        if path[0] == 'ping':            
            return [ 'pong' ]
        
        if path[0] == 'echo':
            doc = { 'Path': path[1:], 'Options': opts }
            if self.app.is_cgi:
                doc.update({ k:v for k,v in os.environ.items() if k.startswith('HTTP_') or k.startswith('REMOTE_') })
            return  doc
        
