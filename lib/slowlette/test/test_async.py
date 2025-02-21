# test_async.py

import asyncio
import slowlette


class MyApp(slowlette.App):
    @slowlette.get('/hello')
    async def hello(self, delay:float=0):
        if delay > 0:
            await asyncio.sleep(delay)
        return f"hello after {delay} sleep"

    
app = MyApp()

'''
to run the app as a ASGI server, run:
$ uvicorn test_slowlette:app
'''

    
if __name__ == '__main__':
    app.run(
#        ssl_keyfile='key.pem', ssl_certfile='cert.pem'   # to use HTTP/2
    )
