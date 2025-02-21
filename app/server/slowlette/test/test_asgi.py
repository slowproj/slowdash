#! /usr/bin/python3



async def app(scope, receive, send):
    if scope.get('type', None) != 'http':
        return

    await send({
        'type': 'http.response.start',
        'status': 200,
        'headers': [(b'content-type', b'text/plain')]
    })
    await send({
        'type': 'http.response.body',
        'body': b'hello, ASGI!'
    })




import uvicorn
uvicorn.run(app)
    
