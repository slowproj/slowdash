# Created by Sanshiro Enomoto on 14 February 2024 #


import sys, time, asyncio, logging

import slowlette
from sd_component import Component


class PubsubComponent(Component):
    topics = [ 'current_data' ]
    
    def __init__(self, app, project):
        super().__init__(app, project)
        
        self.enabled = app.is_async
        self.websockets = {}
        self.current_data_cache = {}
        

    def public_config(self):
        return { 'pubsub': {
            'enabled': self.enabled,
            'subscribers': { topic:len(self.websockets.get(topic,[])) for topic in self.topics },
        }}

    
    @slowlette.websocket('/ws/subscribe/{topic}')
    async def subscribe(self, topic:str, websocket:slowlette.WebSocket):
        if topic not in self.topics:
            return None
        
        try:
            await websocket.accept()
            logging.info(f"WebSocket Connected: {topic}")
        except:
            return None

        if topic not in self.websockets:
            self.websockets[topic] = set()
        self.websockets[topic].add(websocket)
            
        try:
            while True:
                message = await websocket.receive()
                if message is not None and len(message) > 0:
                    logging.info(f"WS-RCV: {topic}: {repr(message)}");
                    try:
                        await self.app.request(f'/publish/{topic}', message)
                    except Exception as e:
                        logging.error(f'Error on re-publishing subpub message in topic "{topic}": {e}')
        except slowlette.ConnectionClosed:
            logging.info("WebSocket Closed")
        except Exception as e:
            logging.info(f"WebSocket Closed by error: {e}")
        finally:
            self.websockets[topic].remove(websocket)

            
    @slowlette.post('/api/publish/{topic}')
    async def publish(self, topic:str, data:bytes):
        try:
            await self.app.request(f'/consume/{topic}', data)
        except Exception as e:
            logging.error(f'Error on consuming subpub message in topic "{topic}": {e}')
            
        try:
            await asyncio.gather(*(ws.send(data.decode()) for ws in self.websockets.get(topic, [])))
        except Exception as e:
            logging.info(f"WebSocket Error: {e}")


    @slowlette.post('api/consume/current_data')
    async def cache_current_data(self, doc:slowlette.DictJSON):
        """caches the publised data for future data queries
        - holds only the last data for each channel
        - holds only single time-point data (e.g., objects and scalars)
        """
        
        for name, data in doc:
            t, x = data.get('t', None), data.get('x', None)
            if type(t) == list:
                if len(t) == 1:
                    t = t[0]
                else:
                    continue
            if t is None or x is None:
                continue
            try:
                t = float(t) + float(data.get('start_time', 0))
                self.current_data_cache[name] = (t, data)
            except:
                continue

        return True

    
    class CacheMergerResponse(slowlette.Response):
        def __init__(self, channels, length, to, cache):
            super().__init__(content={})
            self.channels = channels.split(',')
            self.to = to if to > 0 else to + time.time() + 3
            self.frm = self.to - length
            self.cache = cache

            
        def merge_response(self, response) -> None:
            """inserts cached data only when
              - The "response" parameter (from datasource) does not include the data for the channel, and
              - the cached data is a single point time-series (e.g., data object or scalar)
            """
            
            if response.content is None:
                response.content = {}
            elif type(response.content) is not dict:
                return super().merge_response(response)

            self.content = {}
            for ch in self.channels:
                if ch in response.content:
                    continue
                t,x = self.cache.get(ch, (None, None))
                if t is not None and t >= self.frm and t <= self.to:
                    self.content[ch] = x

            return super().merge_response(response)

            
    @slowlette.get('/api/data/{channels}')
    async def get_pubsub_cache(self, channels:str, length:float=3600, to:float=0):
        return self.CacheMergerResponse(channels, length, to, self.current_data_cache)


    @slowlette.get('/api/channels')
    async def get_cache_channels(self):
        channels = []
        for ch, (t, data) in self.current_data_cache.items():
            x = data.get('x', {})
            if 'y' in x:
                datatype = 'graph'
            elif 'bins' in x:
                datatype = 'histogram'
            elif 'table' in x:
                datatype = 'table'
            elif 'tree' in x:
                datatype = 'tree'
            else:
                datatype = 'unknown'
            channels.append({ 'name': ch, 'type': datatype, 'current': True })

        return channels
