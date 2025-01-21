#! /usr/bin/python3


# temporary until SlowAPI becomes a package
import sys, os
sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir))


import slowapi


class Fruit:
    def __init__(self, name:str):
        self.name = name
        
    @slowapi.get('/hello')
    def hello(self):
        return [f'I am a {self.name}']

class AbortHello:
    @slowapi.get('/hello')
    def hello(self, request:slowapi.Request):
        request.abort()

    
class MyApp(slowapi.App):
    def __init__(self):
        super().__init__()
        self.slowapi.include(Fruit('peach'))
        #self.slowapi.include(AbortHello())
        self.slowapi.include(Fruit('melon'))

    @slowapi.get('/hello')
    def hello(self):
        return ['Hello.']

    
app = MyApp()


if __name__ == '__main__':
    print(app.slowapi('/hello'))

    app.run()
