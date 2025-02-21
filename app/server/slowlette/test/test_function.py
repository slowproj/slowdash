#! /usr/bin/python3


# temporary until Slowlette becomes a package
import sys, os, asyncio
sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir))


import slowlette
app = slowlette.Slowlette()
        
@app.get('/')
def home(self):
    return "I'm home"

@app.get('/hello/{name}')
def hello(self, name:str="there"):
    return f"hello {name}"




async def main():
    print(await app.slowlette('/'))
    print(await app.slowlette('/hello/Slowy'))

    
if __name__ == '__main__':
    asyncio.run(main())
    app.run()
