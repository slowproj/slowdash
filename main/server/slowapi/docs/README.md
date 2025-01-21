# SlowAPI

SlowAPI is a Web-server microframework in Python. Like FastAPI (or Flask), URLs are parsed, parameters are extacted, and the requests are routed to user code. Unlike FastAPI (or Flask), requests are bound to class instance methods, not to functions. One HTTP request can be handled by multiple user handlers, and the responses are aggregated. This design is made for dynamic plug-in systems with the chain-of-responsibility scheme. SlowAPI implements WSGI.


## Dependencies
- Python >=3.9


## Examples
### A Complete Web App with Simple GET

```python
# testapp.py

import slowapi

class App(slowapi.App):
    @slowapi.get('/'):
    def home(self):
        return 'say hello to "/hello"'

    @slowapi.get('/hello'):
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
import slowapi

class App(slowapi.App):
    @slowapi.get('/hello/{name}')
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
import slowapi

class App(slowapi.App):
    @slowapi.get('/hello/{name}')
    def hello(self, name:str, message:str='how are you', repeat:int=3):
        return f'hello, {name}.' + f' {message}' * repeat

app = App()
```


### Receiving the full path and/or query parameters
```python
import slowapi

class App(slowapi.App):
    @slowapi.get('/echo/{*}')
    def hello(self, path:list, query:dict):
        return f'path: {path}, query: {query}'

app = App()
```

- `{*}` matches any path elements.
- A list of decoded URL path is set to the (last; should be only one) argument of a type `list`.
- A dict of decoded URL query is set to the (last) argument of a type `dict`.


### Receiving the entire request
```python
import slowapi

class App(slowapi.App):
    @slowapi.get('/{*}')
    def hello(self, request:slowpi.Request):
        return f'header: {request.headers}'

app = App()
```
The `Request` object has the following attributes:
- `method` (str): request method (`GET` etc.)
- `path` (list[str]): URL path
- `query` (dict[str,str]): URL query
- `headers` (dict[str,str]): HTTP request header items
- `body` (bytes): request body


### Simple POST
```python
import slowapi

class App(slowapi.App):
    @slowapi.post('/hello/{name}')
    def hello(self, name:str, message:bytes):
        return f'hello, {name}. You sent me "{message.decode()}"'

app = App()
```

- The request body is set to the (last) argument of a type of `bytes`.


### POST with JSON document body
#### for dict data
```python
import slowapi

class App(slowapi.App):
    @slowapi.post('/hello/{name}')
    def hello(self, name:str, doc:DictJSON):  # if body in not a dict in JSON, a response 400 (Bad Request) will be returned
        item = doc.get('item', 'nothing')
        return f'hello, {name}. You gave me {item}'

app = App()
```

#### for any data in JSON
```python
import slowapi

class App(slowapi.App):
    @slowapi.post('/hello/{name}')
    def hello(self, name:str, doc:JSON):
        item = doc.get('item', 'nothing')   # this will make a runtime error if the body is not dict
        return f'hello, {name}. You gave me {item}'

app = App()
```

- The request body is parsed as JSON and the value is set to the (last) argument of a type `slowpy.JSON` or `slowpy.DictJSON`.
- Use `JSON.value()` to get a value of the native Python types (`dict`, `list`, `str`, ...).
- Use `dict(doc)` or `list(doc)` to convert to native Python dict or list.
- If the content is dict (or list), most common dict (list) methods are available in JSON-type data:
  - For dict: `doc[key]`, `key in doc`, `for key in doc:`, `doc.get(value, default)`, `doc.items()`, ...
  - For list: `doc[index]`,`len(doc)`, `for v in doc:`, ...


### Multiple Handlers
```python
import slowapi

class Fruit():
    def __init__(self, name:str):
        self.name = name

    @slowapi.get('/hello')
    def hello(self):
        return [f'I am a {sefl.name}']

class App(slowapi.App):
    def __init__(self):
        super().__init__()
        self.include(Fruit('peach'))
        self.include(Fruit('melon'))

    @slowapi.get('/hello')
    def hello(self):
        return ['Hello.']

app = App()
```

```bash
curl http://localhost:8000/hello | jq
[
  "Hello.",
  "I am a peach",
  "I am a melon"
]
```

- If responses are all `list`, they are combined with `append()`.
- If resopnses are all `dict`, they are combined with `update()`.
- If responses are all `str`, they are concatenated with a new-line in between.
- If a response is `None`, it will not be included.
- If all the responses are `None`, a status of 404 (Not Found) is replied.
- If one of the responses are error (code >= 400), an error is replied without content; the largest status code is taken.

The behavior is customizable by providing an useer response aggregator.


### Middleware
```python
import slowapi

class App(slowapi.App):
    @slowapi.get('/hello'):
    def hello(self):
        return 'hello, how are you?'

# test authentication username and password
key = slowpy.BasicAuthentication.generate_key(username='api', password='slow')

app = App()
app.add_middleware(slowpi.BasicAuthentication(auth_list=[key]))
```

```bash
curl http://localhost:8000/hello
```
(nothing will be shown as the access is denied; add `-v` option to see details)

```bash
curl http://api:slow@localhost:8000/hello
```
(this time a response (`hello, how are you?`) will be shown)

As a SlowAPI app can already have mutiple handlers (sub-app) in a chain, there is no difference between a (sub)app and a middleware; if the (sub)app behaves like a middleware, such as modifying the requests for the subsequent (sub)apps and/or modifying the responses from the (sub)apps, it is a middleware. If a handler is added by `app.add_middleware(subapp)`, the `subapp` handlers are inserted before the `app` handlers, whereas `app.include(subapp)` appends `subapp` to `app`.

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
class FileServer(slowapi.App):
    def __init__(self, html_dir, base_path=None, exclude_base_path=None):
    """
    Note:
      - If the base_path is given (e.g., "html"), return files under the path.
      - If the exclude_base_path is given (e.g., "api"), requests staring with it are not handled.
    """
        ....

    @slowapi.get('/'):
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
