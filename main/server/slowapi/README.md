# SlowAPI

## Description
SlowAPI is a Web-server microframework. Like FastAPI (or Flask), URLs are parsed, parameters are extacted, and the requests are routed to user code. In contrast to FastAPI / Flask, requests are bound to class instance methods. One request can be handled by multiple user handlers, and the responses are aggregated. SlowAPI implements WSGI.


## Examples
### Complete Web App with Simple GET

```python
# testapp.py

from slowapi import SlowAPI

class App(SlowAPI):
    @SlowAPI.get('/hello'):
    def hello(self):
        return 'hello, how are you?'

app = App()

if __name__ == '__main__'
    app.run()
```

```bash
python3 testapp.py
```

```bash
curl http://localhost:8000/hello
```


### Running as WSGI
```bash
gunicorn testapp:app
```
- Like Flask/FastAPI, instance of SlowAPI (or its subclass) is a callable WSGI entry point.
- ASGI is currently not implemented.


### GET with URL path parameters
```python
class App(SlowAPI):
    @SlowAPI.get('/hello/{name}')
    def hello(self, name:str):
        return f'hello, {name}'
```
- FastAPI style parameter binding with types, optionally with a default value


### GET with URL query parameters
```python
class App(SlowAPI):
    @SlowAPI.get('/hello/{name}')
    def hello(self, name:str, message:str='how are you', repeat:int=3):
        return f'hello, {name}.' + f' {message}' * repeat
```

### Receiving all path and/or query parameters
```python
class App(SlowAPI):
    @SlowAPI.get('/echo')
    def hello(self, path:list, query:dict):
        return f'path: {path}, query: {query}'
```
- A list of decoded URL path is set to the (last; should be only one) argument of a type `list`.
- A dict of decoded URL query is set to the (last) argument of a type `dict`.

### Simple POST
```python
class App(SlowAPI):
    @SlowAPI.post('/hello/{name}')
    def hello(self, name:str, message:bytes):
        return f'hello, {name}. You gave me {message.decode()}'
```
- The request body is set to the (last) argument of a type of `bytes`.


### POST with JSON data
```python
from slowapi import SlowAPI, JsonDocument
class App(SlowAPI):
    @SlowAPI.post('/hello/{name}')
    def hello(self, name:str, doc:JsonDocument):
        message = doc.get('message', 'nothing')
        return f'hello, {name}. You gave me {message}'
```
- The request body is parsed as JSON and the value is set to the (last) argument of a type `slowpy.JsonDocument`.
- Use `JsonDocument.json()` to get a value of the native Python types (`dict`, `list`, `str`, ...).
- Use `dict(doc)` or `list(doc)` to convert to native Python dict or list.
- If the content is dict (or list), most common dict (list) methods are available in JsonDocument:
  - For dict: `doc[key]`, `key in doc`, `for key in doc:`, `doc.get(value, default)`, `doc.items()`, ...
  - For list: `doc[index]`,`len(doc)`, `for v in doc:`, ...


### Multiple Handlers
```python
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
```

```bash
curl http://localhost:8000/hello | jq
[
  "Hello.",
  "I am a peach",
  "I am an orange"
]
```

- If responses are all `list`, they are combined with `append()`.
- If resopnses are all `dict`, they are combined with `update()`.
- If responses are all `str`, they are concatenated with a new-line in between.
- If a response is None, it will not be included.
- If all the responses are None, a status of 404 (Not Found) is replied.
- If one of the responses are error (code >= 400), an error is replied without content; the largest status code is taken.
