# test_multiple.py

import slowlette


class Fruit:
    def __init__(self, name:str):
        self.name = name
        
    @slowlette.get('/hello')
    def hello(self):
        return [f'I am a {self.name}']

class AbortHello:
    @slowlette.get('/hello')
    def hello(self, request:slowlette.Request):
        request.abort()

class MyApp(slowlette.App):
    def __init__(self):
        super().__init__()
        self.slowlette.include(Fruit('peach'))
        #self.slowlette.include(AbortHello())
        self.slowlette.include(Fruit('melon'))

    @slowlette.get('/hello')
    def hello(self):
        return ['Hello.']

    
app = MyApp()


    
if __name__ == '__main__':
    if True:
        import asyncio
        async def main():
            print(await app.slowlette('/hello'))
        asyncio.run(main())
    
    app.run()
