# Created by Sanshiro Enomoto on 31 December 2024 #

import sys, os, time, json, logging

import slowlette
from sd_component import Component


class MiscApiComponent(Component):
    def __init__(self, app, project):
        super().__init__(app, project)

    @slowlette.get('/api/ping')
    def ping(self):
        return 'pong'

    
    @slowlette.get('/api/echo')
    def echo(self, path:list, opts:dict):
        if self.app.is_cgi:
            env = { k:v for k,v in os.environ.items() if k.startswith('HTTP_') or k.startswith('REMOTE_') }
        else:
            env = {}
            
        return { 'path': path, 'opts': opts, 'env': env }


    @slowlette.get('/api/data/{*}')
    async def api_as_data(self, request:slowlette.Request, length:float=3600, to:float=0):
        path_channels = request.path_str[len('/api/data/'):]   # channel name might contain "/"
        channels = path_channels.split(',') if path_channels else []
        
        result = {}
        now = time.time()
        start = (to if to > 0 else to + now) - length
        
        for ch in channels:
            if not ch.startswith('@api:'):
                continue
            key = ch[len('@api:'):]
            
            value = await self.app.request(key)
            if value is None:
                x = {}            
            elif isinstance(value, dict):
                x = { 'tree': value }
            elif isinstance(value, numbers.Real):
                x = value
            else:
                x = str(value)
                    
            result[ch] = { 'start': start, 't': now - start, 'x': x }
            
        return result
    
