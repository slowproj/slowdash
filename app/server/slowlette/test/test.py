#! /usr/bin/python3


# temporary until Slowlette becomes a package
import sys, os
sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir))


import slowlette, asyncio


class MyApp:
        
    @slowlette.get('/')  # example for the simplest GET
    def home(self):
        return "I'm home"


    @slowlette.get('/hello/{name}')   # name from path, with default
    def hello(self, name:str="there"):
        return f"hello {name}"


    @slowlette.get('/echo/{*}')     # extra path parameters; a list-type arg receives the request path
    def echo(self, path:list):
        return path[1:]

    
    @slowlette.get('/headers')     # getting the entire Request
    def header(self, request:slowlette.Request):
        return { k:v for k,v in request.headers.items() if v is not None }

    
    @slowlette.post('/message')  # example for POST
    def message(self, name:str, doc:bytes):  # name is from options, doc is from request body
        return {'message1': f"Dear {name},\n{doc.decode()}"}


    @slowlette.post('/message')   # multiple responses will be aggregated
    async def message2(self, name:str, doc:bytes):
        return {'message2': f"I said to {name}, {doc.decode()}"}


    @slowlette.get('/source')  # example to return a blob
    def source(self):
        return slowlette.Response(content_type='text/plain', content=open('slowlette.py', 'rb').read())


    @slowlette.delete('/trash')  # example for DELETE
    def delete_trash(self):
        sys.stderr.write("Trash Deleted\n")
        return slowlette.Response(200)


    @slowlette.get('/deci')   # test to return a non-JSONable type
    def deci(self, num:float=10, den:float=3):
        import decimal
        return { "decimal": decimal.Decimal(num)/decimal.Decimal(den), "float": num/den }


    @slowlette.on_event('startup')
    def initialize(self):
        print("INITIALIZED")

        
    @slowlette.on_event('shutdown')
    def finalize(self):
        print("FINALIZED")

    
app = slowlette.App(MyApp())
'''
to run the app as a ASGI server, run:
$ uvicorn test_slowlette:app
'''


wsgi_app = slowlette.WSGI(app)
'''
to run the app as a WSGI server, run:
$ gunicorn test_slowlette:wsgi_app
'''



async def main():
    ### test responses ###
    print(await app.slowlette('/'))
    print(await app.slowlette('/hello'))
    print(await app.slowlette('/hello/Slowy'))
    print(await app.slowlette('/message?name=you', b"how are you doing?"))
    print(await app.slowlette('/echo/hello/Slowy'))
    print(await app.slowlette('/home'))  # does not exist
    #print(await app.slowlette_get('/source'))
    print(await app.slowlette(slowlette.Request('/trash', method='delete')))
    print(await app.slowlette('/deci?den=3'))


    
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
