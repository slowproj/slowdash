#! /usr/bin/python3


# temporary until Slowlette becomes a package
import sys, os, asyncio
sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir))


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



async def main():
    print(await app.slowlette('/hello'))


if __name__ == '__main__':
    asyncio.run(main())
    app.run()
