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
    slowlette.FileServer('../../../web', exclude='/api', drop_exclude_prefix=True, index_file="welcome.html")
)



if __name__ == '__main__':
    if True:
        import asyncio
        async def main():
            print(await app.slowlette('/Warning.png'))
            print(await app.slowlette('/api'))
            print(await app.slowlette('/api/hello/slowlette'))
        asyncio.run(main())
    
    app.run()
