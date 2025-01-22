#! /usr/bin/python3


# temporary until SlowAPI becomes a package
import sys, os
sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir))


import slowapi
app = slowapi.SlowAPI()
        
@app.get('/')
def home(self):
    return "I'm home"

@app.get('/hello/{name}')
def hello(self, name:str="there"):
    return f"hello {name}"


if __name__ == '__main__':
    print(app.slowapi('/'))
    print(app.slowapi('/hello/Slowy'))
    app.run()
