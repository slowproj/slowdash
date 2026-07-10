# Created by Sanshiro Enomoto on 9 July 2026 #

import json


class EventStream:
    def __init__(self, receive_func, send_func):
        self.receive_func = receive_func
        self.send_func = send_func
        self.is_accepted = False
        self.is_closed = False


    async def accept(self):
        if self.is_accepted:
            return
        await self.send_func({
            'type': 'http.response.start',
            'status': 200,
            'headers': [
                (b'content-type', b'text/event-stream; charset=utf-8'),
                (b'cache-control', b'no-cache'),
                (b'x-accel-buffering', b'no'),
            ],
        })
        self.is_accepted = True


    async def close(self, code=1000):
        if self.is_closed:
            return
        await self.accept()
        await self.send_func({
            'type': 'http.response.body',
            'body': b'',
            'more_body': False,
        })
        self.is_closed = True

        
    async def send(self, data, *, event=None, id=None, retry=None):
        await self.accept()

        lines = []
        if id is not None:
            lines.append(f'id: {id}')
        if event is not None:
            lines.append(f'event: {event}')
        if retry is not None:
            lines.append(f'retry: {retry}')

        if type(data) is bytes:
            text = data.decode()
        elif type(data) is str:
            text = data
        else:
            text = json.dumps(data)

        for line in text.splitlines() or ['']:
            lines.append(f'data: {line}')

        payload = ('\n'.join(lines) + '\n\n').encode()
    
        await self.send_func({
            'type': 'http.response.body',
            'body': payload,
            'more_body': True,
        })


    async def comment(self, text=''):
        await self.accept()
        lines = str(text).splitlines() or ['']
        body = ''.join(f': {line}\n' for line in lines) + '\n'
        await self.send_func({
            'type': 'http.response.body',
            'body': body.encode(),
            'more_body': True,
        })


    async def wait_disconnected(self):
        while True:
            message = await self.receive_func()
            if message['type'] == 'http.disconnect':
                raise EventStreamConnectionClosed()



class EventStreamConnectionClosed(Exception):
    pass
