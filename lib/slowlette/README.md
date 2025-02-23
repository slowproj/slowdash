# Slowlette

Slowlette is a Web-server micro-framework in Python. Like FastAPI (or Flask), URLs are parsed, parameters are extracted, and the requests are routed to user code. Unlike FastAPI or Flask, requests in Slowlette can be bound to methods of multiple class instances, not just to functions or a single instance. However, binding to standalone functions (as in FastAPI/Flask) is also supported. One HTTP request can be handled by multiple user handlers, for example, multiple instances of a user class or a combination of different classes and functions, and the responses are aggregated in a customizable way. This is designed for dynamic plug-in systems (where each plugin might return partial data) with the chain-of-responsibility scheme. Slowlette implements both ASGI and WSGI.


## Dependencies
- Python >=3.9
- uvicorn to use ASGI 
- (nothing is necessary for WSGI, though gunicorn can be used)

## Usage
### A Complete Web App with Simple GET

```python
# testapp.py

import slowlette

class App(slowlette.App):
    @slowlette.get('/')
    def home(self):
        return 'feel at home'

    @slowlette.get('/hello')
    def say_hello(self):
        return 'Hello, Slowlette!'

app = App()

if __name__ == '__main__':
    app.run()
```
- Very similar to FastAPI, except that URLs are associated with class methods. Unlike FastAPI, the `app` instance is created after the binding is described. (Important for creating multiple handler instances.)

#### Running the example
Like FastAPI/Flask, running the script above will start an HTTP server at port 8000.
```bash
python3 testapp.py
```
Now open `http://localhost:8000/hello` in your browser, or run:
```bash
curl http://localhost:8000/hello
```
And you should see the response:
```text
Hello, Slowlette!
```

#### Running via external ASGI server
Like FastAPI, Slowlette App object implements ASGI, and any external ASGI server can be used.
```bash
uvicorn testapp:app
```

#### Not inheriting from slowlette.App
The base class, `slowlette.App`, has only three attributes, listed below:
- `slowlette`: Slowlette connection point
- `__call__(self, scope, receive, send)`: ASGI entry point
- `run(self, port, **kwargs)`: Execution start point

Given this small number of attributes, the likelihood of name conflicts with user classes should be minimal.
Nevertheless, it is also possible to create a user class independently from Slowlette and pass it to Slowlette later.
```python
import slowlette

class MyApp:
    @slowlette.get('/hello')
    def say_hello(self):
        return 'hello, how are you?'

app = slowlette.App(MyApp())

if __name__ == '__main__':
    app.run()
```
Once you have created the `app` instance, the usage is essentially the same as before.

#### Performance overhead
Whether the user class is inherited from `slowlette.App` or not, the Slowlette decorators (such as `@slowlette.get()`) do not modify the function signature, and the decorated user methods can be used as they are defined in the user code. There is no additional performance overhead with the Slowlette decorators.


### Binding to functions
By creating an instance of Slowlette, functions, instead of class methods, can be bound to URL endpoints, in a very similar way as FastAPI and Flask.
```python
import slowlette

app = slowlette.Slowlette()

@app.get('/hello')
def say_hello():
    return 'hello, how are you?'

if __name__ == '__main__':
    app.run()
```

### GET with URL path parameters
```python
import slowlette

class App(slowlette.App):
    @slowlette.get('/hello/{name}')
    def hello(self, name:str):
        return f'hello, {name}'

app = App()
```

- FastAPI style parameter binding with types, optionally with a default value
- If a parameter for an argument without a default value is not in the URL, the URL will not match and the handler (`hello()` method in the example) will not be called.
- Return value of a handler must be:
  - `str` for a `text/plain` reply
  - `list` or `dict` for an `application/json` reply
  - `slowlette.FileResponse` object for file fetching
  - `slowlette.Response` object for full flexibility
  - `None` if the request is not applicable


### GET with URL query parameters
```python
import slowlette

class App(slowlette.App):
    @slowlette.get('/hello/{name}')
    def hello(self, name:str, message:str='how are you', repeat:int=3):
        return f'hello, {name}.' + f' {message}' * repeat

app = App()
```

### Async handlers
With ASGI, if the bound method is `async`, requests are handled asynchronously.
```python
import slowlette

class App(slowlette.App):
    @slowlette.get('/hello')
    async def hello(self, delay:float=0):
        if delay > 0:
            await asyncio.sleep(delay)
        return f"hello after {delay} sleep"

app = App()
```


### Receiving the full path and/or query parameters
```python
import slowlette

class App(slowlette.App):
    @slowlette.get('/echo/{*}')
    def echo(self, path:list, query:dict):
        return f'path: {path}, query: {query}'

app = App()
```

- `{*}` matches any path elements.
- A list of decoded URL path is set to the (last; should be only one) argument of a type `list`.
- A dict of decoded URL query is set to the (last) argument of a type `dict`.


### Receiving the entire request
```python
import slowlette

class App(slowlette.App):
    @slowlette.get('/{*}')
    def header(self, request:slowlette.Request):
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
import slowlette

class App(slowlette.App):
    @slowlette.post('/hello/{name}')
    def hello(self, name:str, message:bytes):
        return f'hello, {name}. You sent me "{message.decode()}"'

app = App()
```

- The request body is set to the (last) argument of a type of `bytes`.


### POST with JSON document body
#### for dict data
```python
import slowlette

class App(slowlette.App):
    @slowlette.post('/hello/{name}')
    def hello(self, name:str, doc:DictJSON):  # if body in not a dict in JSON, a response 400 (Bad Request) will be returned
        item = doc.get('item', 'nothing')
        return f'hello, {name}. You gave me {item}'

app = App()
```
- The request body is parsed as `dict` in JSON and the value is set to the (last) argument of a type `slowlette.DictJSON`.
- If the content cannot be parsed as a dict, the handler will not be called and an error response (400) will be returned.
- The DictJSON object (`doc`) implements most common dict operations, such as `doc[key]`, `key in doc`, `for key in doc:`, `doc.get(value, default)`, `doc.items()`, ...
- use `doc.value()` or `dict(doc)` to get a native Python dict object.

#### for any data in JSON
```python
import slowlette

class App(slowlette.App):
    @slowlette.post('/hello/{name}')
    def hello(self, name:str, doc:JSON):
        item = doc.get('item', 'nothing')   # this will make a runtime error if the body is not dict
        return f'hello, {name}. You gave me {item}'

app = App()
```

- The request body is parsed as JSON and the value is set to the (last) argument of a type `slowlette.JSON`.
- If the content cannot be parsed as JSON, the handler will not be called and an error response (400) will be returned.
- Use `JSON.value()` to get a value of the native Python types (`dict`, `list`, `str`, ...).
- Use `dict(doc)` or `list(doc)` to convert to native Python dict or list.
- If the content is dict (or list), most common dict (list) methods are available in JSON-type data:
  - For dict: `doc[key]`, `key in doc`, `for key in doc:`, `doc.get(value, default)`, `doc.items()`, ...
  - For list: `doc[index]`,`len(doc)`, `for v in doc:`, ...


### Lifespan Events
The structure is basically the same as FastAPI:
```python
import slowlette

class App(slowlette.App):
    @slowlette.on_event('startup')
    async def startup(self):
        print("SlowApp Server started")
        
    @slowlette.on_event('shutdown')
    async def shutdown(self):
        print("SlowApp Server stopped")

app = App()
```
- Currently `startup` and `shutdown` are implemented


### WebSocket
The structure is basically the same as FastAPI:
```python
import slowlette

class App(slowlette.App):
    @slowlette.websocket('/ws')
    async def ws_echo(self, websocket:slowlette.WebSocket):
        await websocket.accept()
        try:
            while True:
                message = await websocket.receive_text()
                await websocket.send_text(f'Received: {message}')
        except slowlette.ConnectionClosed:
            print("WebSocket Closed")

app = App()
```
- WebSocket is available only with ASGI.


### Multiple Handlers for the same URL
```python
import slowlette

class Fruit():
    def __init__(self, name:str):
        self.name = name

    @slowlette.get('/hello')
    def hello(self):
        return [f'I am a {self.name}']

class App(slowlette.App):
    def __init__(self):
        super().__init__()
        self.slowlette.include(Fruit('peach'))
        self.slowlette.include(Fruit('melon'))

    @slowlette.get('/hello')
    def hello(self):
        return ['Hello.']

app = App()
```

By sending a request to the `/hello` endpoint, to which three App instances are bound:
```bash
curl http://localhost:8000/hello | jq
```
You will get a result of three responses aggregated:
```text
[
  "Hello.",
  "I am a peach",
  "I am a melon"
]
```

- If responses are all `list`, they are combined with `append()`.
- If responses are all `dict`, they are combined with `update()` (recursively).
- If responses are all `str`, they are concatenated with a new-line in between.
- If a response is `None`, it will not be included.
- If all the responses are `None`, a 404 status (Not Found) is replied.
- If one of the responses is an error (code >= 400), an error is replied without content; the largest status code is taken.

The behavior is customizable by providing a user response aggregator, as explained below.

Instances of `slowlette.Slowlette` used to bind functions in the example above can also be included or include other sub-apps.


### Middleware
As a Slowlette app can already have multiple handlers (sub-app) in a chain, there is no difference between a (sub)app and a middleware; if the (sub)app behaves like a middleware, such as modifying the requests for the subsequent (sub)apps and/or modifying the responses from the (sub)apps, it is a middleware. 

The middleware example below drops the path prefix of `/api` from all the requests:
```python
import slowlette

class DropPrefix:
    def __init__(self, prefix):
        self.prefix = 'api'

    @slowlette.route('/{*}')
    def handle(request: Request):
        if len(request.path) > 0 and request.path[0] == self.prefix:
            request.path = request.path[1:]
        return Response()

class App(slowlette.App):
    def __init__(self):
        super().__init__()
        self.slowlette.add_middleware(DropPrefix('api'))

    @slowlette.get('/hello')
    def hello(self):
        return 'Hello, Middleware.'

app = App()
```

In this example, access to `/api/hello/` will be routed to the method bound to `/hello`, after the middleware that drops the `/api` prefix:
```bash
curl http://localhost:8000/api/hello
```

The `@route()` decorator can be used to handle all the request methods, not specific to one such as `@get()`. The path rule of `/{*}` will capture all the URL. 

The empty response returned here will be replaced with an aggregated responses from the subsequent handlers.

If a (sub)app is added by `app.add_middleware(subapp)`, the `subapp` handlers are inserted before the `app` handlers, whereas `app.include(subapp)` appends `subapp` handlers to `app`. 

Multiple middlewares can be appended, and they will be processed in the order of appending, before the main `app` handlers and sub-app handlers are called.

A middleware that modifies responses can be implemented by returning a custom response with an overridden aggregation method (`Response.merge_response(self, response:Response)`).


### Ready-to-use Middlewares

#### HTTP Basic Authentication
`BasicAuthentication(auth_list: list[str])`

The `auth_list` is a list of keys, where each key looks like:
`api:$2a$12$D2.....`, which is the same key format used by Apache (type "2a").
A key can be generated by:
```
key = slowlette.BasicAuthentication.generate_key('api', 'slow')
```

#### File Server
`FileServer(filedir, *, prefix='', index_file=None, exclude=None, drop_exclude_prefix=False, ext_allow=None, ext_deny=None)`

The file server handles GET requests to send back files stored in `filedir`. The request path, optionally with `prefix` that will be dropped, is the relative path from the `filedir`. For security reasons, file names cannot contain special characters other than a few selected ones (`_`, `-`, `+`, `=`, `,`, `.`, `:`), and the first letter of each path element must be an alphabet or digit. Also, the path cannot start with a Windows drive letter (like `c:`), even if Slowlette runs on non-Windows. POST and DELETE are not implemented.

- `filedir` (str): path to a filesystem directory
- `prefix` (str): URL path to bind this app (e.g., `/webfile`)
- `index_file` (str): index file when the path is empty (i.e., `/`)
- `exclude` (str): URL path not to be handled (e.g., prefix=`/app`, exclude=`/app/api`)
 - `drop_exclude_prefix` (bool): if True, the prefix is removed from the requet path if the request is for an excluded path (e.g., for exclude `/api`, the request path of `api/userlist` becomes `/userlist`)
 - `ext_allow` (list[str]): a list of file extensions to allow accessing
 - `ext_deny` (list[str]): a list of file extensions not to allow accessing

### Custom Response Aggregation
A handler can make a user aggregator by returning an instance of a custom Response class with an overridden `merge_response()` method, as explained above.

```python
import slowlette

class MyExclusiveApp:
    class MyExclusiveResponse(Response):
        def merge_response(self, response:Response)->None
            # example: do not merge the responses from the subsequent handlers
            pass

    @slowlette.route('/hello')
    def hello():
        response = MyExclusiveResponse()
        response.append('hello, there is no one else here.')
        return response
```
This method is useful if the method returns a data structure that requires a certain way to merge other data.

In addition to that, a user app class can override a method to aggregate all the individual responses from all the handlers within the class, to provide full flexibility. To do this, make a custom `Router` with an overridden `merge_responses()` method:

```python
import slowlette

class MyRouter(slowlette.Router):
    def merge_responses(responses: list[Response]) -> Response:
        response = Response()
        for r in responses:
            response = ....   # aggregate responses here
        return response
```

Then use this as a `slowlette` of the user app:
```python
class MyApp(slowlette.App):
    def __init__(self):
        self.slowlette = MyRouter()
        super().__init__()
```
Calling `super().__init__()` later is a little bit more efficient, as it does not replace `self.slowlette` if it is already defined.


### Basic Authentication
```python
import slowlette

class App(slowlette.App):
    @slowlette.get('/hello')
    def hello(self):
        return 'hello, how are you?'

# test authentication username and password
# once generated, store the key separately
key = slowlette.BasicAuthentication.generate_key(username='api', password='slow')

app = App()
app.add_middleware(slowlette.BasicAuthentication(auth_list=[key]))
```

If HTTP is used, nothing will be returned, as the access is denied. (Add `-v` option to see details.)
```bash
curl http://localhost:8000/hello -v
```
```text
...
> GET /hello HTTP/1.1
> Host: localhost:8000
> User-Agent: curl/8.5.0
...
< HTTP/1.1 401 Unauthorized
```

Now with the credentials:
```bash
curl http://api:slow@localhost:8000/hello
```
You will get the expected result:
```text
hello, how are you?
```


### HTTPS and HTTP/2
HTTP/2 is enabled only with TLS. Provide TLS key files to use HTTPS.
```python
if __name__ == '__main__':
    app.run(ssl_keyfile='key.pem', ssl_certfile='cert.pem')
```

#### Memo: Generating a certificate
##### Temporary Self-Signed
```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout key.pem -out cert.pem
```
##### Let's Encrypt if you have a domain:
```bash
sudo apt install certbot
sudo certbot certonly --standalone -d YOUR.DOMAIN.NAME
```
This will create files under `/etc/letsencript/live/YOUR.DOMAIN.NAME`
- private key: `privkey.pem`
- server certificate: `cert.pem`
- full chain: `fullchain.pem`

### WSGI
In addition to ASGI, WSGI can be used. The `slowlette.WSGI(app)` function wraps the ASGI App (standard Slowlette App) and returns a WSGI app.
```python
# testapp.py

import slowlette

class App(slowlette.App):
    @slowlette.get('/hello')
    def hello(self):
        return 'hello, how are you?'

app = App()   # ASGI App
wsgi_app = slowlette.WSGI(app)

if __name__ == '__main__':
    wsgi_app.run()
```
The script can be executed as an HTTP server with WSGI:
```bash
python3 ./testapp.py
```

Or it can be used with any WSGI server:
```bash
gunicorn testapp:wsgi_app
```

Note:
- Every HTTP request is handled sequentially, even with async handlers.
- A dedicated async event loop is created for each request.
  Code that assumes the same event loop among requests (typical in DB connection pool) cannot be used.


## TODOs
- File templates
- App.mount('path', app)
- OpenAPI document generation
- GraphQL chain processing (thanks ChatGPT for the idea!)
  
