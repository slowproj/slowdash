# Created by Sanshiro Enomoto on 27 January 2025 #


class WebSocket:
    def __init__(self, receive_func, send_func):
        self.receive_func = receive_func
        self.send_func = send_func


    async def accept(self):
        await self.send_func({'type': 'websocket.accept'})


    async def close(self, code=1000):
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
            raise ConnectionClosed()

        
    async def send(self, data):
        if type(data) is bytes:
            await self.send_func({'type': 'websocket.send', 'bytes': data})
        else:
            await self.send_func({'type': 'websocket.send', 'text': str(data)})



class ConnectionClosed(Exception):
    pass

