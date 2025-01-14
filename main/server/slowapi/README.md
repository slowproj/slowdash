# SlowAPI
## Description
FastAPI style minimal micro Web-server framework, APIs are bound to class instances (as opposed to functions like Flask and FastAPI). Multiple handlers can be assigned to the same URL, and multiple resopnses are aggregated.

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

### GET with URL path parameters
```python
    @SlowAPI.get('/hello/{name}')
    def hello(self, name:str)
        return f'hello, {name}'
```

### GET with URL query parameters
```python
    @SlowAPI.get('/hello/{name}')
    def hello(self, name:str, message:str='how are you', repeat:int=3):
        return f'hello, {name}.' + f' {message}' * repeat
```

### Simple POST
```python
    @SlowAPI.post('/hello/{name}')
    def hello(self, name:str, message:bytes):
        return f'hello, {name}. You gave me {message.decode()}'
```

### POST with JSON data
```python
from slowapi import SlowAPI, JsonDocument
class App(SlowAPI):
    @SlowAPI.post('/hello/{name}')
    def hello(self, name:str, doc:JsonDocument):
        message = doc.get('message', 'nothing')
        return f'hello, {name}. You gave me {message}'
```

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

- If responses are all `list`, they will be combined with `append()`.
- If resopnses are all `dict`, they will be combined with `update()`.
- If responses are all `str`, they will be concatenated with a new-line in between.
- If one of the responses are error (code >= 400), an error will be returned.
