# SlowAPI

SlowAPI is a Web-server microframework. Like FastAPI (or Flask), URLs are parsed, parameters are extacted, and the requests are routed to user code. In contrast to FastAPI / Flask, requests are bound to class instance methods, not to functions. One HTTP request can be handled by multiple user handlers, and the responses are aggregated. This design is made for dynamic plug-in systems with the chain-of-responsibility scheme. SlowAPI implements WSGI.


## Dependencies
- Python >=3.9


## Examples
### A Complete Web App with Simple GET

```python
# testapp.py

from slowapi import SlowAPI

class App(SlowAPI):
    @SlowAPI.get('/'):
    def home(self):
        return 'say hello to "/hello"'

    @SlowAPI.get('/hello'):
    def hello(self):
        return 'hello, how are you?'

app = App()

if __name__ == '__main__'
    app.run()
```
- Very similar to FastAPI, except that URLs are associated to class methods. Unlike FastAPI, the `app` instance is created after the binding is described. (Important for creating multiple handler instances.)

#### Running the example
```bash
python3 testapp.py
```

```bash
curl http://localhost:8000/hello
```


#### Running via WSGI
```bash
gunicorn testapp:app
```

- Like Flask/FastAPI, an instance of SlowAPI (or its subclass) is a callable WSGI entry point.
- ASGI is currently not implemented.


### GET with URL path parameters
```python
from slowapi import SlowAPI

class App(SlowAPI):
    @SlowAPI.get('/hello/{name}')
    def hello(self, name:str):
        return f'hello, {name}'

app = App()
```

- FastAPI style parameter binding with types, optionally with a default value
- If a parameter for an argument without a default value is not in the URL, the URL will not match and the handler (`hello()` method in the example) will not be called.
- Return value of a handler must be:
  - `str` for a `text/plain` reply
  - `list` or `dict` for an `application/json` reply
  - `None` if the request is not applicable
  - `slowapi.Response` object for full flexibility
  - (TODO: `slowapi.File` object; maybe with template substitutions)


### GET with URL query parameters
```python
from slowapi import SlowAPI

class App(SlowAPI):
    @SlowAPI.get('/hello/{name}')
    def hello(self, name:str, message:str='how are you', repeat:int=3):
        return f'hello, {name}.' + f' {message}' * repeat

app = App()
```


### Receiving the full path and/or query parameters
```python
from slowapi import SlowAPI

class App(SlowAPI):
    @SlowAPI.get('/echo')
    def hello(self, path:list, query:dict):
        return f'path: {path}, query: {query}'

app = App()
```

- A list of decoded URL path is set to the (last; should be only one) argument of a type `list`.
- A dict of decoded URL query is set to the (last) argument of a type `dict`.


### Simple POST
```python
from slowapi import SlowAPI

class App(SlowAPI):
    @SlowAPI.post('/hello/{name}')
    def hello(self, name:str, message:bytes):
        return f'hello, {name}. You sent me "{message.decode()}"'

app = App()
```

- The request body is set to the (last) argument of a type of `bytes`.


### POST with JSON data
```python
from slowapi import SlowAPI, JSONDocument

class App(SlowAPI):
    @SlowAPI.post('/hello/{name}')
    def hello(self, name:str, doc:JSONDocument):
        item = doc.get('item', 'nothing')
        return f'hello, {name}. You gave me {item}'

app = App()
```

- The request body is parsed as JSON and the value is set to the (last) argument of a type `slowpy.JSONDocument`.
- Use `JSONDocument.json()` to get a value of the native Python types (`dict`, `list`, `str`, ...).
- Use `dict(doc)` or `list(doc)` to convert to native Python dict or list.
- If the content is dict (or list), most common dict (list) methods are available in JSONDocument:
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
- If a response is `None`, it will not be included.
- If all the responses are `None`, a status of 404 (Not Found) is replied.
- If one of the responses are error (code >= 400), an error is replied without content; the largest status code is taken.


## TODOs

### Request object
- modifiable -> middleware
  - URL rewrite
  - auth
  - user info

### File content response / template processing
```python
class FileResponse(Response):
    def __init__(self, path, content_type=None):
        # maybe the content_type can be inferred from the file extension
        self.content_type = ....
        self.content = ....
```

```python
class TemplateResponse(FileResponse):
    def __init__(self, template_engine, params, path, content_type=None):
        super().__init__(path, content_type)
        if self.content is not None:
            self.content = template_engine.render(self.content, params)
```


### File Server API
```python
class FileServer(SlowAPI):
    def __init__(self, html_dir, base_path=None, exclude_base_path=None):
    """
    Note:
      - If the base_path is given (e.g., "html"), return files under the path.
      - If the exclude_base_path is given (e.g., "api"), requests staring with it are not handled.
    """
        ....

    @SlowAPI.get('/'):
    def get_file(self, path:list):
        # sanity checks
        ....
        return FileResponse(....
```

This can be "included" into a SlowAPI app:
```
app = MyApp()
app.include(FileServer(....))
```
