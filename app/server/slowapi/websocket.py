# Created by Sanshiro Enomoto on 27 January 2025 #


class WebSocket:
    def __init__(self, receive, send):
        self.receive = receive
        self.send = send


    async def accept(self):
        await self.send({'type': 'websocket.accept'})


    async def close(self, code=1000):
        await self.send({'type': 'websocket.close', 'code': code})

        
    async def receive_text(self):
        message = await self.receive()
        if message['type'] == 'websocket.receive':
            return message.get('text', '')
        if message['type'] == 'websocket.disconnect':
            raise ConnectionClosed()
        
    async def send_text(self, text):
        await self.send({'type': 'websocket.send', 'text': text})



class ConnectionClosed(Exception):
    pass

