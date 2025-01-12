#! /usr/bin/python3


import sys
from slowapi import SlowAPI, Response


class MyApp(SlowAPI):
        
    @SlowAPI.get('/')  # example for the simplest GET
    def home(self):
        return "I'm home"


    @SlowAPI.get('/hello/{name}')   # name from path, with default
    def hello(self, name:str="there"):
        return f"hello {name}"


    @SlowAPI.post('/message')  # example for POST
    def message(self, name:str, doc:bytes):  # name is from options, doc is from request body
        return {'message1': f"Dear {name},\n{doc.decode()}"}


    @SlowAPI.post('/message')   # multiple responses will be aggregated
    def message2(self, name:str, doc:bytes):
        return {'message2': f"I said to {name}, {doc.decode()}"}


    @SlowAPI.get('/source')  # example to return a blob
    def source(self):
        return Response(content_type='text/plain', content=open('slowapi.py', 'rb').read())


    @SlowAPI.delete('/trash')  # example for DELETE
    def delete_trash(self):
        sys.stderr.write("Trash Deleted\n")
        return Response(200)


    
app = MyApp()

'''
to run the app as a WSGI server, run:
$ gunicorn test_slowapi:app
'''

if __name__ == '__main__':
    print(app.handle_get_request('/'))
    print(app.handle_get_request('/hello'))
    print(app.handle_get_request('/hello/SlowDash'))
    print(app.handle_post_request('/message?name=you', b"how are you doing?"))
    print(app.handle_get_request('/home'))
    #print(app.handle_get_request('/source'))
    print(app.handle_delete_request('/trash'))

    app.run(port=18881)
