# Created by Sanshiro Enomoto on 31 December 2024 #

import sys, os, logging

import slowlette
from sd_component import Component


class MiscApiComponent(Component):
    def __init__(self, app, project):
        super().__init__(app, project)

    @slowlette.get('/ping')
    def ping(self):
        return ['pong']

    
    @slowlette.get('/echo')
    def echo(self, path:list, opts:dict):
        if self.app.is_cgi:
            env = { k:v for k,v in os.environ.items() if k.startswith('HTTP_') or k.startswith('REMOTE_') }
        else:
            env = {}
            
        return { 'Path': path, 'Opts': opts, 'Env': env }
