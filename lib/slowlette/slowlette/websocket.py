# Created by Sanshiro Enomoto on 27 January 2025 #

import asyncio


class WebSocket:
    def __init__(self, receive_func, send_func):
        self.receive_func = receive_func
        self.send_func = send_func
        self.is_accepted = False
        self.is_closed = False


    async def accept(self):
        if self.is_accepted:
            return
        await self.send_func({'type': 'websocket.accept'})
        self.is_accepted = True


    async def close(self, code=1000, timeout=3.0):
        if self.is_closed:
            return
        self.is_closed = True

        try:
            await asyncio.wait_for(self._send_end(code), timeout=timeout)
        except (asyncio.TimeoutError, ConnectionError, OSError):
            # peer not reading (e.g., suspended PC); give up, transport is left to the server
            pass

        
    async def _send_end(self, code):
        await self.send_func({'type': 'websocket.close', 'code': code})

        
    async def receive(self):
        message = await self.receive_func()
        if message['type'] == 'websocket.receive':
            if 'text' in message:
                return message['text']
            elif 'bytes' in message:
                return message['bytes']
            else:
                return None
        if message['type'] == 'websocket.disconnect':
            raise WebSocketConnectionClosed()

        
    async def send(self, data):
        if type(data) is bytes:
            await self.send_func({'type': 'websocket.send', 'bytes': data})
        else:
            await self.send_func({'type': 'websocket.send', 'text': str(data)})



class WebSocketConnectionClosed(Exception):
    pass

