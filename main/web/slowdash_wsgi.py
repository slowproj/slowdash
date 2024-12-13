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
        start_response('500', [])
        return [ b'' ]

    path = environ.get('PATH_INFO', '/')
    query = environ.get('QUERY_STRING', '')
    method = environ.get('REQUEST_METHOD', 'GET')
    content_length = os.environ.get('CONTENT_LENGTH', '')
    url = path + ('?' + query if len(query) > 0 else '')

    
    if method == 'GET':
        reply = webui.process_get_request(url)
            
    elif method == 'POST':
        try:
            content_length = int(content_length)
        except:
            start_response('400', [])
            return [ b'' ]
        if content_length > 1024*1024*1024:
            start_response('507', [])
            return [ b'' ]
        doc = sys.stdin.buffer.read(content_length)
        reply = webui.process_post_request(url, doc)
        
    elif method == 'DELETE':
        reply = webui.process_delete_request(url)
            
    else:
        start_response('500', [])
        return [ b'' ]

    
    if reply is None:
        start_response('500', [])
        return [ b'' ]
    elif reply.response >= 400 or reply.content_type is None:
        status, headers = str(reply.response), []
    else:
        status = str(reply.response)
        headers = [ ('Content-type', reply.content_type) ]

    start_response(status, headers)
    return [ reply.get_content() ]
