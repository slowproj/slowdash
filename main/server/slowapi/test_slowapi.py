#! /usr/bin/python3


from slowapi import SlowAPI, Response


class MyApp(SlowAPI):
    def __init__(self):
        super().__init__()
    
        
    @SlowAPI.get('/')
    def home(self):
        return "I'm home"


    @SlowAPI.get('/hello/{name}')
    def hello(self, name:str="you"):
        return f"hello {name}"


    @SlowAPI.post('/message')
    def message(self, name:str, doc:bytes):
        return {'message': f"Dear {name},\n{doc.decode()}"}


    @SlowAPI.post('/message')
    def message2(self, name:str, doc:bytes):
        return {'message_2nd': "I'm fine."}


    @SlowAPI.get('/source')
    def source(self):
        return Response(content_type='text/plain', content=open('slowapi.py', 'rb').read())


    
app = MyApp()

print(app.handle_get_request('/'))
print(app.handle_get_request('/hello/SlowDash'))
print(app.handle_post_request('/message?name=you', "how are you doing?".encode()))
print(app.handle_get_request('/home'))
#print(app.handle_get_request('/source'))
