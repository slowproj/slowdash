# Created by Sanshiro Enomoto on 1 April 2026 #

from slowpy.control import control_system as ctrl


class Dash:
    def __init__(self, slowdash_url: str|None = None):
        self.http = None
        
        if slowdash_url is not None:
            self.connect(slowdash_url)
            
        
    def connect(self, slowdash_url:str):
        if slowdash_url is None:
            return
        
        try:
            self.http = ctrl.async_http(slowdash_url)
        except Exception as e:
            logging.error(e)
            self.http = None


    async def aio_close(self):
        if self.http is not None:
            await self.http.aio_close()

            
    async def aio_ping(self):
        if self.http is None:
            return None
        
        return await self.http.path('/api/ping').json().aio_get()

    
    async def aio_get_config(self):
        if self.http is None:
            return None
        
        return await self.http.path('/api/config').json().aio_get()

    
    async def aio_get_channels(self):
        if self.http is None:
            return None
        
        return await self.http.path('/api/channels').json().aio_get()

    
    async def aio_get_data(self, channels, length=3600, **options):
        if self.http is None:
            return None
        
        if type(channels) is list:
            url = f"/api/data/{','.join(channels)}"
        else:
            url = f"/api/data/{channels}"
        opts = { 'length': length }
        opts.update(options)
        
        return await self.http.path(url,**opts).json().aio_get()

