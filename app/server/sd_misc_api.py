# Created by Sanshiro Enomoto on 31 December 2024 #

import sys, os, logging

import slowlette
from sd_component import Component


class MiscApiComponent(Component):
    def __init__(self, app, project):
        super().__init__(app, project)

        # allow access to SlowDash JS library via "/api/webfiles/slowdash"
        self.slowlette.add_middleware(slowlette.FileServer(
            filedir = os.path.join(app.project.sys_dir, 'app', 'site'),
            prefix = '/webfiles/slowdash',
            ext_allow = ['.mjs', '.css']
        ))
        # allow access to Project user web files
        self.slowlette.add_middleware(slowlette.FileServer(
            filedir = os.path.join(app.project_dir, 'webfiles'),
            prefix = '/webfiles',
            exclude = '/webfiles/api',
        ))
        
        
    @slowlette.get('/webfiles/api/{*}')
    async def api_redirect(self, path:list, opts:dict):
        url = '/'.join(path[1:])
        if len(opts):
            url += '?' + '&'.join([f'{k}={v}' for k,v in opts.items()])
        return await self.app.request(url)

    
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
