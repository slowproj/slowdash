# test_function.py

import slowlette


app = slowlette.Slowlette()


@app.get('/')
def home(self):
    return "I'm home"


@app.get('/hello/{name}')
def hello(self, name:str="there"):
    return f"hello {name}"



if __name__ == '__main__':
    if True:
        import asyncio
        async def main():
            print(await app.slowlette('/'))
            print(await app.slowlette('/hello/Slowy'))
        asyncio.run(main())
    
    app.run()
