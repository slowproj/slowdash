#! /usr/bin/python3
# Created by Sanshiro Enomoto on 3 Sep 2021 #

import sys, os

from slowdash_cgi_config import sys_dir, project_dir
sys.path.insert(0, os.path.join(sys_dir, 'main', 'server'))
from slowdash import WebUI


def main():    
    path = os.environ.get('PATH_INFO', '/')
    query = os.environ.get('QUERY_STRING', '')
    method = os.environ.get('REQUEST_METHOD', '')
    content_length = os.environ.get('CONTENT_LENGTH', '')
    
    if len(query):
        url = path + '?' + query
    else:
        url = path

    webui = WebUI(project_dir, is_cgi=True)

    if method == 'GET':
        reply = webui.process_get_request(url)
        if (
            (reply is None) or
            (reply.content_type is None) or
            ((reply.content is None) and (reply.content_readable is None))
        ):
            sys.stdout.write('Status: 500\n\n')
            return
        elif reply.response >= 400:
            sys.stdout.write('Status: %d\n\n' % reply.response)
            return
    
        sys.stdout.write('Content-type: %s\n\n' % reply.content_type)
        sys.stdout.flush()
        reply.write_to(sys.stdout.buffer).destroy()

    elif method == 'POST':
        try:
            content_length = int(content_length)
        except:
            sys.stdout.write('Status: 400\n\n')
            return
        if content_length > 1024*1024*1024:
            sys.stdout.write('Status: 507\n\n')
            return
        
        doc = sys.stdin.buffer.read(content_length)
        
        reply = webui.process_post_request(url, doc)
        if (reply is None):
            sys.stdout.write('Status: 500\n\n')
            return

        sys.stdout.write('Status: %d\n\n' % reply.response)

    else:
        sys.stdout.write('Status: 500\n\n')
        return

    
if __name__ == '__main__':
    main()
