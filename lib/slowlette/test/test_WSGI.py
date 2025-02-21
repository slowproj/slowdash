# test.py

import sys
import slowlette


class MyApp:
        
    @slowlette.get('/')  # example for the simplest GET
    def home(self):
        return "I'm home"


    @slowlette.get('/hello/{name}')   # name from path, with default
    def hello(self, name:str="there"):
        return f"hello {name}"


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


    
if __name__ == '__main__':
    wsgi_app.run()
