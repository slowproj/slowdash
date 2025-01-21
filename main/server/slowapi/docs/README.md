# SlowAPI

SlowAPI is a Web-server micro-framework in Python. Like FastAPI (or Flask), URLs are parsed, parameters are extracted, and the requests are routed to user code. Unlike FastAPI (or Flask), requests are bound to class instance methods, not to functions. One HTTP request can be handled by multiple user handlers, and the responses are aggregated. This design is made for dynamic plug-in systems with the chain-of-responsibility scheme. SlowAPI implements WSGI.


## Dependencies
- Python >=3.9


## Usage
### A Complete Web App with Simple GET

```python
# testapp.py

import slowapi

class App(slowapi.App):
    @slowapi.get('/'):
    def home(self):
        return 'feel at home'

    @slowapi.get('/hello'):
    def say_hello(self):
        return 'hello, how are you?'

app = App()

if __name__ == '__main__'
    app.run()
```
- Very similar to FastAPI, except that URLs are associated to class methods. Unlike FastAPI, the `app` instance is created after the binding is described. (Important for creating multiple handler instances.)

#### Running the example
Like FastAPI/Flask, running the script above will start a HTTP server at port 8000.
```bash
python3 testapp.py
```

```bash
curl http://localhost:8000/hello
```

#### Running via WSGI
Like FastAPI/Flask, the SlowAPI App implements the WSGI interface and any WSGI servers can be used.
```bash
gunicorn testapp:app
```

- An instance of SlowAPI App (or its subclass) is a callable WSGI entry point.
- ASGI is currently not implemented.


#### Not inheriting from slowapi.App
The base class, `slowapi.App`, has the following only three attributes:
- `slowapi`: SlowAPI connection point
- `__call__(environ, start_response)`: WSGI entry point
- `run()`: Execution start point

Therefore the chance of name conflicts with user classes is minimal.
Nevertheless, it is also possible to make an user class independently from SlowAPI, and pass it to SlowAPI later:
```python
import slowapi

class MyApp:
    @slowapi.get('/hello'):
    def say_hello(self):
        return 'hello, how are you?'

app = slowapi.App(MyApp())

if __name__ == '__main__'
    app.run()
```

The SlowAPI decorators (such as `@slowapi.get()`) do not modify the function signature, and the decorated user methods can be used as they are defined in the user code. There is no added overhead with this.

Once `app` is made, the rest is the same.


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
    def hello(self, request:slowapi.Request):
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
- The request body is parsed as `dict` in JSON and the value is set to the (last) argument of a type `slowapi.DictJSON`.
- If the content cannot be not parsed as a dict, the handler will not be called and an error response (400) will be returned.
- The DictJSON object (`doc`) implements most common dict operations, such as `doc[key]`, `key in doc`, `for key in doc:`, `doc.get(value, default)`, `doc.items()`, ...
- use `doc.value()` or `dict(doc)` to get a native Python dict object.

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

- The request body is parsed as JSON and the value is set to the (last) argument of a type `slowapi.JSON`.
- If the content cannot be not parsed as JSON, the handler will not be called and an error response (400) will be returned.
- Use `JSON.value()` to get a value of the native Python types (`dict`, `list`, `str`, ...).
- Use `dict(doc)` or `list(doc)` to convert to native Python dict or list.
- If the content is dict (or list), most common dict (list) methods are available in JSON-type data:
  - For dict: `doc[key]`, `key in doc`, `for key in doc:`, `doc.get(value, default)`, `doc.items()`, ...
  - For list: `doc[index]`,`len(doc)`, `for v in doc:`, ...


### Multiple Handlers for the same URL
```python
import slowapi

class Fruit():
    def __init__(self, name:str):
        self.name = name

    @slowapi.get('/hello')
    def hello(self):
        return [f'I am a {self.name}']

class App(slowapi.App):
    def __init__(self):
        super().__init__()
        self.slowapi.include(Fruit('peach'))
        self.slowapi.include(Fruit('melon'))

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
- If responses are all `dict`, they are combined with `update()`.
- If responses are all `str`, they are concatenated with a new-line in between.
- If a response is `None`, it will not be included.
- If all the responses are `None`, a status of 404 (Not Found) is replied.
- If one of the responses are error (code >= 400), an error is replied without content; the largest status code is taken.

The behavior is customizable by providing an user response aggregator.


### Middleware
```python
import slowapi

class App(slowapi.App):
    @slowapi.get('/hello'):
    def hello(self):
        return 'hello, how are you?'

# test authentication username and password
key = slowapi.BasicAuthentication.generate_key(username='api', password='slow')

app = App()
app.add_middleware(slowapi.BasicAuthentication(auth_list=[key]))
```

```bash
curl http://localhost:8000/hello
```
(nothing will be shown as the access is denied; add `-v` option to see details)

```bash
curl http://api:slow@localhost:8000/hello
```
(this time a response (`hello, how are you?`) will be shown)

As a SlowAPI app can already have multiple handlers (sub-app) in a chain, there is no difference between a (sub)app and a middleware; if the (sub)app behaves like a middleware, such as modifying the requests for the subsequent (sub)apps and/or modifying the responses from the (sub)apps, it is a middleware. If a (sub)app is added by `app.add_middleware(subapp)`, the `subapp` handlers are inserted before the `app` handlers, whereas `app.include(subapp)` appends `subapp` handlers to `app`.

The `@route()` decorator can be used to handle all the request methods, not specific to one such as `@get()`. The path rule of `/{*}` will capture all the URL. 

The middleware example below drops the path prefix of `/api` from all the requests:
```python
import slowapi

class MyMiddleware_DropApiPrefix:
    @slowapi.route('/{*}')
    def handle(request: Request):
        if len(request.path) > 0 and request.path[0] == 'api':
            request.path = request.path[1:]
        return Response()
```

The empty response returned here will be replaced with an aggregated responses from the subsequent handlers.

A middleware that modifies responses can be implemented by returning a custom response with an overridden aggregation method (`Response.merge_response(self, response:Response)`.


### Custom Response Aggregation
A handler can make a user aggregator by returning an instance of a custom Response class with an overridden `merge_response()` method, as explained above.

In addition to that, an user app class can override a method to aggregate all the individual responses from all the handlers within the class. To do this, make a custom `Router` with an overridden `merge_responses()` method:

```python
import slowapi

class MyRouter(slowapi.Router):
    def merge_responses(responses: list[Response]) -> Response:
        response = Response()
        for r in responses:
            response = ....   # aggregate responses here
        return response
```

Then use this as a `slowapi` of the user app:
```python
class MyApp(slowapi.App):
    def __init__(self):
        self.slowapi = MyRouter()
        super().__init__()
```
Calling `super().__init__()` later is a little bit more efficient, as it does not replace `self.slowapi` if it is already defined.


## TODOs
- Async API
- ASGI interface
- File templates
