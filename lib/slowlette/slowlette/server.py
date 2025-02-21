# Created by Sanshiro Enomoto on 18 January 2025 #

        
import sys, signal, asyncio, logging
from wsgiref.util import request_uri
from wsgiref.simple_server import make_server, WSGIRequestHandler

from .request import Request
from .websocket import WebSocket
from .router import Router


async def dispatch_asgi(app, scope, receive, send):
    """ASGI interface
    Args: see the ASGI specification
    """
    
    if scope['type'] == 'lifespan':
        while True:
            try:
                message = await receive()
            except asyncio.CancelledError:
                await app.slowlette.dispatch_event("shutdown")
                return
            if message['type'] == 'lifespan.startup':
                await app.slowlette.dispatch_event("startup")
                await send({'type': 'lifespan.startup.complete'})
            elif message['type'] == 'lifespan.shutdown':
                await app.slowlette.dispatch_event("shutdown")
                await send({'type': 'lifespan.shutdown.complete'})

    method = scope.get('method', '').upper()
    url = scope.get('raw_path', b'').decode()
    query = scope.get('query_string', b'')
    if len(query) > 0:
        url += '?' + query.decode()           
    headers = { k.decode():v.decode() for k,v in scope['headers'] }

    if scope['type'] == 'websocket':
        logging.info(f'WEBSOCKET: {url}')
        return await app.slowlette.websocket(Request(url, method='WEBSOCKET', headers=headers), WebSocket(receive, send))
    elif scope['type'] != 'http':
        logging.warning(f'ASGI Request not handled: type={scope["type"]}')
        return
    
    body = None
    if method == 'POST':
        try:
            content_length = int(headers.get('content-length', None))
        except:
            logging.error(f'ASGI_POST: bad content length: {content_length}')
            await send({type:'http.response.start', status:400})
            await send({type:'http.response.body', body:b''})
        if content_length > 1024*1024*1024:
            logging.error(f'ASGI_POST: content length too large: {content_length}')
            await send({type:'http.response.start', status:507})
            await send({type:'http.response.body', body:b''})
        
        body = b''
        if content_length > 0:
            while len(body) < content_length:
                message = await receive()
                if message['type'] == 'http.request':
                    body += message.get('body', b'')
                    if not message.get('more_body',False):
                        break

    response = await app.slowlette(Request(url, method=method, headers=headers, body=body))
    logging.info(f'{method}: {url} -> {response.status_code}')

    await send({
        'type': 'http.response.start',
        'status': response.get_status_code(),
        'headers': [(k.encode(),v.encode()) for k,v in response.get_headers() ]
    })
    await send({
        'type': 'http.response.body',
        'body': response.get_content()
    })

    

def dispatch_wsgi(app, environ, start_response):
    """WSGI interface
    Args: see the WSGI specification
    """
    
    # URL without application basepath (different from request_uri(environ))
    url = environ.get('PATH_INFO', '/')
    query = environ.get('QUERY_STRING', '')
    if len(query) > 0:
        url += '?' + query
    
    method = environ.get('REQUEST_METHOD', 'GET').upper()

    headers = {
        'content-type': environ.get('CONTENT_TYPE', None),
        'content-length': environ.get('CONTENT_LENGTH', None),
        'authorization': environ.get('HTTP_AUTHORIZATION', None),
        'host': environ.get('HTTP_HOST', None),
        'user-agent': environ.get('HTTP_USER_AGENT', None),
        'accept': environ.get('HTTP_ACCEPT', None),
        'referer': environ.get('HTTP_REFERER', None),
        'x-forwarded-for': environ.get('HTTP_X_FORWARDED_FOR', None),
        'x-forwarded-proto': environ.get('HTTP_X_FORWARDED_PROT', None),
        'cookie': environ.get('HTTP_COOKIE', None),
        'cache-control': environ.get('HTTP_CACHE_CONTROL', None),
        'if-modified-since': environ.get('HTTP_IF_MODIFIED_SINCE', None),
    }
        
    body = None
    if method == 'POST':
        try:
            content_length = int(environ.get('CONTENT_LENGTH', ''))
        except:
            logging.error(f'WSGI_POST: bad content length: {content_length}')
            start_response('400 Bad Request', [])
            return [ b'' ]
        if content_length > 1024*1024*1024:
            logging.error(f'WSGI_POST: content length too large: {content_length}')
            start_response('507 Insufficient Storage', [])
            return [ b'' ]
        if content_length > 0:
            body = environ['wsgi.input'].read(content_length)
        else:
            body = b''

    response = asyncio.run(app.slowlette(Request(url, method=method, headers=headers, body=body)))
    logging.info(f'{method}: {url} -> {response.status_code}')
    
    start_response(response.get_status(), response.get_headers())
    return [ response.get_content() ]



def serve_asgi_uvicorn(app, port, **kwargs):
    try:
        import uvicorn
    except:
        logging.error('Unable to import uvicorn Python package: not installed?')
        logging.warn('Falling back to WSGI; async requests will be serialized. WebSockets will not be available.')
        return serve_wsgi_ref(WSGI(app), port, **kwargs)

    async def main():
        config = uvicorn.Config(app, port=port, workers=1, lifespan="on", **kwargs)
        server = uvicorn.Server(config)
        #server.install_signal_handlers=False  # this causes the server not working...
        
        server_task = asyncio.create_task(server.serve())
        
        # overwrite the signal handlers set by uvicorn.Server()        
        await asyncio.sleep(0.1)
        def signal_handler(signum, frame):
            server_task.cancel()
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            await server_task
        except asyncio.CancelledError:
            pass
        
    if ('ssl_keyfile' in kwargs) and ('ssl_certfile' in kwargs):
        is_https = True
    else:
        is_https = False
        
    sys.stderr.write(f'Listening at port {port} (ASGI {"HTTPS" if is_https else "HTTP"})\n')
    asyncio.run(main())
    sys.stderr.write('Terminated\n')    


    
def serve_asgi_hypercorn(app, port, **kwargs):
    try:
        from hypercorn.config import Config
        from hypercorn.asyncio import serve
    except:
        logging.error('Unable to import hypercorn Python package: not installed?')
        logging.warn('Falling back to WSGI; async requests will be serialized. WebSockets will not be available.')
        return serve_wsgi_ref(WSGI(app), port, **kwargs)

    async def main():
        config = Config()
        config.bind = f'0.0.0.0:{port}'
        config.alpn_protocols = ['h2', 'h2c', 'http/1.1']
        config.workers = 1
        config.threads = 1
        if 'ssl_keyfile' in kwargs:
            config.keyfile = kwargs['ssl_keyfile']
        if 'ssl_certfile' in kwargs:
            config.certfile = kwargs['ssl_certfile']
            
        await serve(app, config)
        
    sys.stderr.write(f'Listening at port {port} (ASGI by Hypercorn)\n')
    asyncio.run(main())
    sys.stderr.write('Terminated\n')    


    
def serve_wsgi_gunicorn(app, port, **kwargs):
    try:
        import gunicorn.app.base
    except:
        logging.info('Unable to import gunicorn Python package: not installed?')
        logging.info('Falling back to wsgi_ref')
        return serve_wsgi_ref(app, port, **kwargs)

    class GunicornApp(gunicorn.app.base.BaseApplication):
        def __init__(self, app, **kwargs):
            self.app = app
            self.options = {k:v for k,v in kwargs.items()}
            super().__init__()

        def load_config(self):
            for key, value in self.options.items():
                if key in self.cfg.settings and value is not None:
                    self.cfg.set(key.lower(), value)
            logging.debug(self.cfg)

        def load(self):
            return self.app
        
    kwargs['bind'] = f'0.0.0.0:{port}'        
    kwargs['workers'] = 1
    if ('ssl_keyfile' in kwargs) and ('ssl_certfile' in kwargs):
        kwargs['keyfile'] = kwargs['ssl_keyfile']
        kwargs['certfile'] = kwargs['ssl_certfile']
        # Using HTTP/2 requres Python package of "httptools" and "h2"
        #kwargs['http'] = kwargs['h2']
        is_https = True
    else:
        is_https = False

    Request.is_async = False

    
    # gunicorn SHOULD handle signals... signals cannot stop the App somehow.
    sys.stderr.write(f'Listening at port {port} (gunicorn WSGI {"HTTPS" if is_https else "HTTP"})\n')
    
    asyncio.run(app.slowlette.dispatch_event('startup'))
    GunicornApp(app, **kwargs).run()
    asyncio.run(app.slowlette.dispatch_event('shutdown'))
    sys.stderr.write('Terminated\n')


    
def serve_wsgi_ref(app, port, **kwargs):
    class RequestHandler(WSGIRequestHandler):
        def log_message(self, fmt, *args):
            pass

    Request.is_async = False

    def signal_handler(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    sys.stderr.write(f'Listening at port {port} (wsgiref WSGI)\n')
    asyncio.run(app.slowlette.dispatch_event('startup'))
    try:
        with make_server('', port, app, handler_class=RequestHandler) as server:
            server.serve_forever()
    except KeyboardInterrupt:
        pass
    asyncio.run(app.slowlette.dispatch_event('shutdown'))
    sys.stderr.write('Terminated\n')    



    
def serve_asgi(app, port, **kwargs):
    return serve_asgi_uvicorn(app, port, **kwargs)
    #return serve_asgi_hypercorn(app, port, **kwargs)

def serve_wsgi(app, port, **kwargs):
    return serve_wsgi_gunicorn(app, port, **kwargs)



class WSGI:
    """ASGI to WSGI Adapter
    """
    def __init__(self, app, serve=serve_wsgi):
        self.app = app
        self.serve = serve
        self.slowlette = app.slowlette


    def __call__(self, environ, start_response):
        """WSGI entry point
        """
        if not hasattr(self, 'slowlette'): # __init__() might not have been called
            self.slowlette = Router(self)
            
        return dispatch_wsgi(self.app, environ, start_response)


    def run(self, port=8000, **kwargs):
        """Run HTTP Server
        """
        self.serve(self, port, **kwargs)
