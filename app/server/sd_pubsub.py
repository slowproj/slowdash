# Created by Sanshiro Enomoto on 14 February 2024 #


import sys, io, asyncio, logging

import slowlette
from sd_component import Component


class PubsubComponent(Component):
    topics = [ 'currentdata' ]
    
    def __init__(self, app, project):
        super().__init__(app, project)
        
        self.enabled = app.is_async
        self.websockets = {}
        

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
                    if topic == 'currentdata':
                        await self.app.request('/control/currentdata', message.encode())
                        await self.app.request('/publish/currentdata', message)
        except slowlette.ConnectionClosed:
            self.websockets[topic].remove(websocket)
            logging.info("WebSocket Closed")
        except Exception as e:
            self.websockets[topic].remove(websocket)
            logging.info(f"WebSocket Closed by error: {e}")

            
    @slowlette.post('/api/publish/{topic}')
    async def publish(self, topic:str, data:bytes):
        try:
            await asyncio.gather(*(ws.send(data.decode()) for ws in self.websockets.get(topic, [])))
        except Exception as e:
            logging.info(f"WebSocket Error: {e}")
