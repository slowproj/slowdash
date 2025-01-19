#! /usr/bin/python3


# temporary until SlowAPI becomes a package
import sys, os
sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir))


import slowapi


class MyApp(slowapi.App):
        
    @slowapi.get('/')
    def home(self):
        return "I'm home"

    @slowapi.get('/hello/{name}')
    def hello(self, name:str="there"):
        return f"hello {name}"


app = MyApp()
app.slowapi_prepend(slowapi.FileServer('../../../web', basepath_exclude='/api', drop_basepath=True, index_file="welcome.html"))

key = slowapi.BasicAuthentication.generate_key('slow', 'dash')
#app.slowapi_prepend(slowapi.BasicAuthentication(auth_list=[key]))


if __name__ == '__main__':
    print(app.slowapi('/Warning.png'))
    print(app.slowapi('/api'))
    print(app.slowapi('/api/hello/you'))
    app.run()
