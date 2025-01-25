# Created by Sanshiro Enomoto on 18 January 2025 #

        
import sys, signal, asyncio, logging
from wsgiref.util import request_uri
from wsgiref.simple_server import make_server, WSGIRequestHandler

from .request import Request


def signal_handler(signum, frame):
    raise KeyboardInterrupt


async def dispatch_asgi(app, scope, receive, send):
    """ASGI interface
    Args: see the ASGI specification
    """
    
    if scope['type'] != 'http':
        if scope['type'] != 'lifespan':
            logging.warning(f'ASGI Request not handled: type={scope["type"]}')
        return
    
    method = scope['method'].upper()
    url = scope['raw_path'].decode()
    if len(scope['query_string']) > 0:
           url += '?' + scope['query_string'].decode()           
    headers = { k.decode():v.decode() for k,v in scope['headers'] }

    logging.info(url)
    
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

    logging.debug(f'{method}: {url}')
    response = await app.slowapi(Request(url, method=method, headers=headers, body=body))

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
    url = request_uri(environ)
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
        
    logging.info(url)
    
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

    response = asyncio.run(app.slowapi(Request(url, method=method, headers=headers, body=body)))
    logging.debug(f'{method}: {url} -> {response.status_code}')
    
    start_response(response.get_status(), response.get_headers())
    return [ response.get_content() ]



def serve_asgi_uvicorn(app, port, **kwargs):
    try:
        import uvicorn
    except:
        logging.error('Unable to import uvicorn Python package: not installed?')
        return
    
    sys.stderr.write(f'Listening at port {port} (ASGI)\n')

    try:
        signal.signal(signal.SIGTERM, signal_handler)
        uvicorn.run(app, port=port, workers=1, **kwargs)
    except KeyboardInterrupt:
        pass
    
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
    if 'ssl_keyfile' in kwargs:
        kwargs['keyfile'] = kwargs['ssl_keyfile']
    if 'ssl_certfile' in kwargs:
        kwargs['certfile'] = kwargs['ssl_certfile']
        
    sys.stderr.write(f'Listening at port {port} (gunicorn WSGI)\n')
    try:
        signal.signal(signal.SIGTERM, signal_handler)
        GunicornApp(app, **kwargs).run()
    except KeyboardInterrupt:
        pass
    sys.stderr.write('Terminated\n')    


    
def serve_wsgi_ref(app, port, **kwargs):
    class RequestHandler(WSGIRequestHandler):
        def log_message(self, fmt, *args):
            pass

    sys.stderr.write(f'Listening at port {port} (wsgiref WSGI)\n')

    try:
        signal.signal(signal.SIGTERM, signal_handler)
        with make_server('', port, app, handler_class=RequestHandler) as server:
            server.serve_forever()
    except KeyboardInterrupt:
        pass
    
    sys.stderr.write('Terminated\n')    



    
def serve_asgi(app, port, **kwargs):
    return serve_asgi_uvicorn(app, port, **kwargs)

def serve_wsgi(app, port, **kwargs):
    return serve_wsgi_gunicorn(app, port, **kwargs)
