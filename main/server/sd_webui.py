#! /usr/bin/env python3
# Created by Sanshiro Enomoto on 3 Sep 2021 #


import sys, os, io, json, logging
from decimal import Decimal
from urllib.parse import urlparse, parse_qsl, unquote


class Reply:
    def __init__(self, response, content_type=None, content=None):
        self.response = response
        self.content_type = content_type
        self.content = content
        self.content_readable = None

        
    def __del__(self):
        if self.content_readable:
            self.content_readable.close()

            
    def get_content(self):
        if self.content_readable is not None:
            self.content = b''
            try:
                while True:
                    chunk = self.content_readable.read(1024*1024)
                    if not chunk:
                        break
                    self.content += chunk
            except Exception as e:
                logging.warning('error on sending out a reply: %s' % str(e))

            try:
                self.content_readable.close()
            except:
                pass
            self.content_readable = None

        if self.content is None:
            return b''
        elif type(self.content) is str:
            return self.content.encode()
        else:
            return self.content

        
    def write_to(self, output):
        if self.content_readable is not None:
            try:
                while True:
                    chunk = self.content_readable.read(1024*1024)
                    if not chunk:
                        break
                    output.write(chunk)
            except Exception as e:
                logging.warning('error on sending out a reply: %s' % str(e))

            try:
                self.content_readable.close()
            except:
                pass
            self.content_readable = None
        
        else:
            if self.content is None:
                pass
            elif type(self.content) is str:
                output.write(self.content.encode())
            else:
                output.write(self.content)
            return

        
            
class WebUI:
    def __init__(self, app):
        self.app = app
        self.auth_list = self.app.project.auth_list        
        self.json_kwargs = {}

        # To convert decimal values into numbers that can be handled by JSON
        def decimal_to_num(obj):
            if isinstance(obj, Decimal):
                return int(obj) if float(obj).is_integer() else float(obj)
        self.json_kwargs['default'] = decimal_to_num

        
    def check_sanity(self, string, accept = []):
        string = string.replace('_', '0').replace('-', '0').replace('.', '0').replace(',', '0').replace(' ', '0')
        string = string.replace(':', '0').replace('[', '0').replace(']', '0')
        for ch in accept:
            string = string.replace(ch, '0')
        return string.isalnum()

    
    def process_get_request(self, url):
        logging.debug(f'GET {url}')
        
        if self.app is None:
            return Reply(404)   # Not Found
        u = urlparse(url)
        path = [ unquote(p) for p in u.path.split('/') ]
        while path.count(''):
            path.remove('')
        if not path:
            logging.error('bad query (empty query): %s' % url)
            return Reply(400)  # Bad Request

        opts = dict()
        for key, value in parse_qsl(u.query):
            key, value = unquote(key), unquote(value)
            if not self.check_sanity(key) or not self.check_sanity(value, accept=['/', '~']):
                logging.error('bad query (invalid char): {"%s": "%s"} in %s' % (key, value, url))
                return Reply(400)   # Bad Request
            opts[key] = value
            
        for element in path:
            if (len(element) == 0) or (not element[0].isalnum() and element[0] not in ['_']):
                logging.error('bad query (invalid first char): %s' % url)
                return Reply(400)     # Bad Request
            if not self.check_sanity(element):
                logging.error('bad query (invalid char): %s' % url)
                return Reply(400)     # Bad Request

        with io.BytesIO() as output:
            result = self.app.process_get(path, opts, output=output)
            if type(result) in [ dict, list ]:
                return Reply(200, 'application/json', json.dumps(result, **self.json_kwargs).encode())
            elif type(result) is int:
                return Reply(result)
            elif type(result) is str:
                return Reply(200, result, output.getvalue())
            elif type(result) is bool:
                if result is True:
                    result = {'status': 'ok'}
                    return Reply(200, 'application/json', json.dumps(result, **self.json_kwargs).encode())
                else:
                    logging.error('Bad request (GET): %s' % url)
                    return Reply(400)     # Bad Request
            else:
                logging.error('Bad URL (GET): %s' % url)
                return Reply(400)       # Bad Request


    def process_post_request(self, url, doc):
        logging.debug(f'POST {url}')
        
        if self.app is None:
            return Reply(404)   # Not Found
        u = urlparse(url)
        path = [ unquote(p) for p in u.path.split('/') ]
        while path.count(''):
            path.remove('')
        for element in path:
            if (len(element) == 0) or not element[0].isalpha():
                logging.error('bad file name (invalid first char): %s' % url)
                return Reply(400)  # Bad Request
            if not element.replace('_', '0').replace('-', '0').replace('~', '0').replace('.', '0').replace(' ', '0').replace(',', '0').isalnum():
                logging.error('bad file name (invalid char): %s' % url)
                return Reply(400)       # Bad Request
        
        opts = dict()
        for key, value in parse_qsl(u.query):
            key, value = unquote(key), unquote(value)
            if not self.check_sanity(key) or not self.check_sanity(value, accept=['/', '~']):
                logging.error('bad query (invalid char): {"%s": "%s"} in %s' % (key, value, url))
                return Reply(400)       # Bad Request
            opts[key] = value
            
        with io.BytesIO() as output:
            result = self.app.process_post(path, opts, doc, output=output)
            if type(result) in [ dict, list ]:
                return Reply(201, 'application/json', json.dumps(result, **self.json_kwargs).encode())
            elif type(result) is int:
                return Reply(result)
            elif type(result) is str:
                return Reply(201, result, output.getvalue())
            elif type(result) is bool:
                if result is True:
                    result = {'status': 'ok'}
                    return Reply(201, 'application/json', json.dumps(result, **self.json_kwargs).encode())
                else:
                    logging.error('Bad request (POST): %s' % url)
                    return Reply(400)       # Bad Request
            else:
                logging.error('Bad URL (POST): %s' % url)
                return Reply(400)       # Bad Request

            
    def process_delete_request(self, url):
        logging.debug(f'DELETE {url}')
        
        if self.app is None:
            return Reply(404)   # Not Found
        u = urlparse(url)
        path = [ unquote(p) for p in u.path.split('/') ]
        while path.count(''):
            path.remove('')
        for element in path:
            if (len(element) == 0) or not element[0].isalpha():
                logging.error('bad file name (invalid first char): %s' % url)
                return Reply(400)  # Bad Request
            if not element.replace('_', '0').replace('-', '0').replace('~', '0').replace('.', '0').replace(' ', '0').isalnum():
                logging.error('bad file name (invalid char): %s' % url)
                return Reply(400)  # Bad Request
        
        result = self.app.process_delete(path)
        if type(result) is int:
            return Reply(result)
        elif type(result) is bool:
            if result is True:
                result = {'status': 'ok'}
                return Reply(200, 'application/json', json.dumps(result, **self.json_kwargs).encode())
            else:
                logging.error('Bad request (DELETE): %s' % url)
                return Reply(400)       # Bad Request
        else:
            logging.error('Bad URL (DELETE): %s' % url)
            return Reply(400)       # Bad Request
