# Created by Sanshiro Enomoto on 14 February 2024 #


import sys, time, copy, asyncio, traceback, logging

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
    async def publish(self, topic:str, data:bytes, sender:str=None):
        try:
            if sender is None:
                await self.app.request(f'/consume/{topic}', data)
            else:
                await self.app.request(f'/consume/{topic}?sender={sender}', data)
        except Exception as e:
            logging.error(f'Error on consuming subpub message in topic "{topic}": {e}')
            logging.error(traceback.format_exc())
            
        try:
            await asyncio.gather(*(ws.send(data.decode()) for ws in self.websockets.get(topic, [])))
        except Exception as e:
            logging.info(f"WebSocket Error: {e}")

        return True


    @slowlette.post('/api/consume/current_data')
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
                self.current_data_cache[name] = (t, copy.deepcopy(data))
            except:
                continue

        return True

    
    class CacheChannelMergerResponse(slowlette.Response):
        def __init__(self, cache):
            super().__init__(content=[])
            self.cache = cache

            
        def merge_response(self, response) -> None:
            if response.content is None:
                response.content = []
            elif type(response.content) is not list:
                super().merge_response(response)
                return
            existing_channels = { x.get('name', '__') for x in response.content }
            
            self.content = []
            for ch, (t, data) in self.cache.items():
                if ch in existing_channels:
                    continue
                x = data.get('x', {})
                
                datatype = 'unknown'
                if type(x) is list and len(x) > 0:
                    if type(x[-1]) in [int, float]:
                        datatype = 'timeseries'
                    else:
                        x = x[-1]
                if type(x) is list:
                    pass
                elif type(x) in [ int, float ]:
                    datatype = 'numeric'
                elif type(x) is dict:
                    if 'y' in x:
                        datatype = 'graph'
                    elif 'bins' in x:
                        datatype = 'histogram'
                    elif 'table' in x:
                        datatype = 'table'
                    elif 'tree' in x:
                        datatype = 'tree'
                else:
                    try:
                        float(x)
                        datatype = 'numeric'
                    except:
                        pass
                    
                self.content.append({ 'name': ch, 'type': datatype, 'current': True })

            super().merge_response(response)

            
    class CacheDataMergerResponse(slowlette.Response):
        def __init__(self, channels, length, to, cache):
            super().__init__(content=None)
            self.channels = channels.split(',')
            self.to = to if to > 0 else to + time.time() + 3
            self.frm = self.to - length
            self.cache = cache

            
        def merge_response(self, response) -> None:
            """append the cached pubsub data to the response (typiaclly data from storage)
               - only if the channel does not exist, or
               - the last data point is older than the cached pubsub data
            """
            
            if response.content is None:
                response.content = {}
            elif type(response.content) is not dict:
                super().merge_response(response)
                return

            for ch in self.channels:
                my_t, my_data = self.cache.get(ch, (None, None))
                if my_t is None or my_t < self.frm or my_t > self.to:
                    continue
                
                if ch not in response.content:
                    response.content[ch] = my_data
                    continue
                    
                data = response.content[ch]
                t0 = data.get('start', 0)
                t = data.get('t', None)
                if type(t) is list:
                    if len(t) == 0 or t0 + t[-1] < my_t - 0.001:
                        data['t'].append(my_t - t0)
                        data['x'].append(my_data.get('x',None))
                elif t is not None:
                    if t0 + t < my_t - 0.001:
                        data['t'] = [ t, my_t - t0 ]
                        data['x'] = [ data.get('x', None), my_data.get('x',None) ]
                else:
                    data['start'] = self.frm
                    data['t'] = my_t - self.frm
                    data['x'] = my_data

            self.content = None
            if len(response.content) > 0:
                response.status_code = 200
                
            super().merge_response(response)

            
    @slowlette.get('/api/channels')
    async def get_cache_channels(self):
        return self.CacheChannelMergerResponse(self.current_data_cache)

    
    @slowlette.get('/api/data/{channels}')
    async def get_cache_data(self, channels:str, length:float=3600, to:float=0):
        return self.CacheDataMergerResponse(channels, length, to, self.current_data_cache)
