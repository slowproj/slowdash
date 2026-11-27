# Created by Sanshiro Enomoto on 31 December 2024 #

import sys, os, time, json, logging

import slowlette
from sd_component import Component


class MiscApiComponent(Component):
    def __init__(self, app, project):
        super().__init__(app, project)

        self._start_time = int(time.time())
        self._uptime = 0
        self._last_slowlette_count = 0
        self._slowlette_rate = '0'
        

    def public_config(self):
        self.project.update()
        config = self.project.config or {}

        doc = {
            'slowdash': {
                'version': self.project.version
            },
            'project': {
                'name': config.get('name', 'Untitled Project'),
                'title': config.get('title', ''),
                'server_url': self.project.server_url,
                'is_secure': self.project.is_secure,
                'is_cgi': self.app.is_cgi,
                'is_command': self.app.is_command,
                'is_async': self.app.is_async,
            },
            'style': config.get('style', {}),
        }
        
        now = time.time()
        uptime = int(now) - self._start_time
        if uptime != self._uptime:
            count = self.app.slowlette.request_count
            rate = (count - self._last_slowlette_count) / (uptime - self._uptime)
            self._uptime = uptime
            self._last_slowlette_count = count
            if rate >= 100:
                self._slowlette_rate = '%.0f' % rate
            elif rate >= 10:
                self._slowlette_rate = '%.1f' % rate
            else:
                self._slowlette_rate = '%.3f' % rate

        doc['slowlette'] = {
            'statistics': {
                'up_time': uptime,
                'requests': self.app.slowlette.request_count,
                'request_rate': self._slowlette_rate,
            },
            'current_requests': [
                f'{(now - req.time):.3f}s, {req}'
                for req in self.app.slowlette.current_requests
            ]
        }

        return doc
    

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
                if 'tree' in value or 'table' in value:
                    x = value
                else:
                    x = { 'tree': value }
            elif isinstance(value, numbers.Real):
                x = value
            else:
                x = str(value)
                    
            result[ch] = { 'start': start, 't': now - start, 'x': x }
            
        return result
    
