#! /usr/bin/python3


# temporary until SlowAPI becomes a package
import sys, os
sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir))


import slowapi, asyncio


class MyApp:
        
    @slowapi.get('/')  # example for the simplest GET
    def home(self):
        return "I'm home"


    @slowapi.get('/hello/{name}')   # name from path, with default
    def hello(self, name:str="there"):
        return f"hello {name}"


    @slowapi.get('/echo/{*}')     # extra path parameters; a list-type arg receives the request path
    def echo(self, path:list):
        return path[1:]

    
    @slowapi.get('/headers')     # getting the entire Request
    def header(self, request:slowapi.Request):
        return { k:v for k,v in request.headers.items() if v is not None }

    
    @slowapi.post('/message')  # example for POST
    def message(self, name:str, doc:bytes):  # name is from options, doc is from request body
        return {'message1': f"Dear {name},\n{doc.decode()}"}


    @slowapi.post('/message')   # multiple responses will be aggregated
    async def message2(self, name:str, doc:bytes):
        return {'message2': f"I said to {name}, {doc.decode()}"}


    @slowapi.get('/source')  # example to return a blob
    def source(self):
        return slowapi.Response(content_type='text/plain', content=open('slowapi.py', 'rb').read())


    @slowapi.delete('/trash')  # example for DELETE
    def delete_trash(self):
        sys.stderr.write("Trash Deleted\n")
        return slowapi.Response(200)


    @slowapi.get('/deci')   # test to return a non-JSONable type
    def deci(self, num:float=10, den:float=3):
        import decimal
        return { "decimal": decimal.Decimal(num)/decimal.Decimal(den), "float": num/den }


app = slowapi.App(MyApp())
'''
to run the app as a ASGI server, run:
$ uvicorn test_slowapi:app
'''


wsgi_app = slowapi.WSGI(app)
'''
to run the app as a WSGI server, run:
$ gunicorn test_slowapi:wsgi_app
'''



async def main():
    ### test responses ###
    print(await app.slowapi('/'))
    print(await app.slowapi('/hello'))
    print(await app.slowapi('/hello/Slowy'))
    print(await app.slowapi('/message?name=you', b"how are you doing?"))
    print(await app.slowapi('/echo/hello/Slowy'))
    print(await app.slowapi('/home'))  # does not exist
    #print(await app.slowapi_get('/source'))
    print(await app.slowapi(slowapi.Request('/trash', method='delete')))
    print(await app.slowapi('/deci?den=3'))


    
if __name__ == '__main__':
    asyncio.run(main())
    
    ### start a HTTP server at default port 8000 ###


    ### ASGI HTTP/2:
    # requres Python package of "httptools" and "h2"
    # to generate a self-certificates:
    #   Self-Signed:    openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout key.pem -out cert.pem
    #   Let's Encrypt:  sudo apt install certbot; sudo certbot cetonly --standalone -d yourdomain.com
    # to check: curl URL -v --http2
    app.run(ssl_keyfile='key.pem', ssl_certfile='cert.pem')

    # WSGI in HTTPS (gunicorn)
    #wsgi_app.run(ssl_keyfile='key.pem', ssl_certfile='cert.pem')

    # WSGI (wsgiref)
    #wsgi_app.run()
