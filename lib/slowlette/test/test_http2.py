# test_http2.py


""" ASGI HTTP/2:
- this uses Hypercorn (configure it in slowlette/server.py)
- to generate a self-certificates:
    - self-signed:    openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout key.pem -out cert.pem
    - Let's Encrypt:  sudo apt install certbot; sudo certbot cetonly --standalone -d yourdomain.com
- to check: curl URL -v --http2
- for a self-signed certificate, curl needs the --insecure option
"""


import slowlette


class MyApp:
    @slowlette.get('/')
    def home(self):
        return "I'm home"

    @slowlette.get('/hello/{name}')
    def hello(self, name:str="there"):
        return f"hello {name}"


app = slowlette.App(MyApp())


    
if __name__ == '__main__':
    # with HTTPS (h2)
    #app.run(ssl_keyfile='key.pem', ssl_certfile='cert.pem')

    # with HTTP (h2c)
    app.run()
