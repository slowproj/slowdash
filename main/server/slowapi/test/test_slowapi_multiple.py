# temporary until SlowAPI becomes a package
import sys, os
sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir))

from slowapi import SlowAPI


class Peach(SlowAPI):
    @SlowAPI.get('/hello')
    def hello(self):
        return ['I am a peach']

    
class Orange(SlowAPI):        
    @SlowAPI.get('/hello')
    def hello(self):
        return ['I am an orange']

    
class App(SlowAPI):
    def __init__(self):
        super().__init__()
        self.include(Peach())
        self.include(Orange())

    @SlowAPI.get('/hello')
    def hello(self):
        return ['Hello.']

    
app = App()


if __name__ == '__main__':
    app.run()
