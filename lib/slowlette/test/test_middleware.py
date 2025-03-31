# test_middleware.py

import slowlette


class MyApp(slowlette.App):
        
    @slowlette.get('/')
    def home(self):
        return "I'm home"

    @slowlette.get('/hello/{name}')
    def hello(self, name:str="there"):
        return f"hello {name}"


app = MyApp()

key = slowlette.BasicAuthentication.generate_key('api', 'slow')
app.slowlette.add_middleware(slowlette.BasicAuthentication(auth_list=[key]))

app.slowlette.add_middleware(
    slowlette.FileServer('..', prefix='file', exclude='/slowlette', index_file="welcome.html")
)



if __name__ == '__main__':
    import logging
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(level=logging.DEBUG)

    
    if True:
        import asyncio
        async def main():
            print(await app.slowlette('/Warning.png'))
            print(await app.slowlette('/api'))
            print(await app.slowlette('/api/hello/slowlette'))
        asyncio.run(main())
    
    app.run()
