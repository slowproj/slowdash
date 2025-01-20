# Created by Sanshiro Enomoto on 18 January 2025 #

        
import sys, signal, logging
from wsgiref.util import request_uri
from wsgiref.simple_server import make_server, WSGIRequestHandler

from .request import Request


def signal_handler(signum, frame):
    raise KeyboardInterrupt


def wsgi(app, environ, start_response):
    """WSGI interface
    Args: see the WSGI specification
    """
    url = request_uri(environ)
    method = environ.get('REQUEST_METHOD', 'GET')

    headers = {
        'Content-Type': environ.get('CONTENT_TYPE', None),
        'Content-Length': environ.get('CONTENT_LENGTH', None),
        'Authorization': environ.get('HTTP_AUTHORIZATION', None),
        'Host': environ.get('HTTP_HOST', None),
        'User-Agent': environ.get('HTTP_USER_AGENT', None),
        'Accept': environ.get('HTTP_ACCEPT', None),
        'Referer': environ.get('HTTP_REFERER', None),
        'X-Forwarded-For': environ.get('HTTP_X_FORWARDED_FOR', None),
        'X-Forwarded-Proto': environ.get('HTTP_X_FORWARDED_PROT', None),
        'Cookie': environ.get('HTTP_COOKIE', None),
        'Cache-Control': environ.get('HTTP_CACHE_CONTROL', None),
        'If-Modified-Since': environ.get('HTTP_IF_MODIFIED_SINCE', None),
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

    logging.debug(f'{method}: {url}')
    response = app.slowapi(Request(url, method=method, headers=headers, body=body))
    
    start_response(response.get_status(), response.get_headers())
    return [ response.get_content() ]



def serve_wsgi(app, port):
    class RequestHandler(WSGIRequestHandler):
        def log_message(self, fmt, *args):
            pass

    sys.stderr.write('Listening at port %d\n' % port)

    try:
        signal.signal(signal.SIGTERM, signal_handler)
        with make_server('', port, app, handler_class=RequestHandler) as server:
            server.serve_forever()
    except KeyboardInterrupt:
        pass
    
    sys.stderr.write('Terminated\n')    
