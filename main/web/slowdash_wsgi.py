#! /usr/bin/python3
# Created by Sanshiro Enomoto on 12 Dec 2024 #

import sys, os

import logging
logging.basicConfig(level=logging.WARNING)

from slowdash_cgi_config import sys_dir, project_dir
sys.path.insert(0, os.path.join(sys_dir, 'main', 'server'))
from slowdash import WebUI


webui = None
is_cgi = False


def application(environ, start_response):
    global webui, is_cgi
    if webui is None:
        webui = WebUI(project_dir, is_cgi=is_cgi)
    if webui.app is None:
        start_response('500 Internal Server Error', [])
        return [ b'' ]

    path = environ.get('PATH_INFO', '/')
    query = environ.get('QUERY_STRING', '')
    method = environ.get('REQUEST_METHOD', 'GET')
    content_length = environ.get('CONTENT_LENGTH', '')
    url = path + ('?' + query if len(query) > 0 else '')

    if method == 'GET':
        reply = webui.process_get_request(url)
            
    elif method == 'POST':
        try:
            content_length = int(content_length)
        except:
            logging.error(f'WSGI_POST: bad content length: {content_length}')
            start_response('400 Bad Request', [])
            return [ b'' ]
        if content_length > 1024*1024*1024:
            logging.error(f'WSGI_POST: content length too large: {content_length}')
            start_response('507 Insufficient Storage', [])
            return [ b'' ]
        doc = environ['wsgi.input'].read(content_length)
        reply = webui.process_post_request(url, doc)
        
    elif method == 'DELETE':
        reply = webui.process_delete_request(url)
            
    else:
        start_response('500 Internal Server Error', [])
        return [ b'' ]

    
    if reply is None:
        start_response('500 Internal Server Error', [])
        return [ b'' ]
    elif reply.response >= 400 or reply.content_type is None:
        response, headers = reply.response, []
    else:
        response = reply.response
        headers = [ ('Content-type', reply.content_type) ]
        
    response_messages = {
        200: 'OK', 201: 'Created',
        400: 'Bad Request', 401: 'Unauthorized', 403: 'Forbidden', 404: 'Not Found',
        500: 'Internal Server Error', 503: 'Service Unavailable',
    }
    status = str(response) + ' ' + response_messages.get(response, 'Unknown Response Code')

    start_response(status, headers)
    return [ reply.get_content() ]
