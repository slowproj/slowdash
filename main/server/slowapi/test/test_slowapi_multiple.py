#! /usr/bin/python3


# temporary until SlowAPI becomes a package
import sys, os
sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir))


from slowapi import App as SlowApp, get as slowget


class Peach(SlowApp):
    @slowget('/hello')
    def hello(self):
        return ['I am a peach']

    
class Orange(SlowApp):        
    @slowget('/hello')
    def hello(self):
        return ['I am an orange']

    
class MyApp(SlowApp):
    def __init__(self):
        super().__init__()
        self.slowapi_include(Peach())
        self.slowapi_include(Orange())

    @slowget('/hello')
    def hello(self):
        return ['Hello.']

    
app = MyApp()


if __name__ == '__main__':
    app.run()
