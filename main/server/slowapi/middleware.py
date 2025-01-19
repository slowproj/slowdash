# Created by Sanshiro Enomoto on 18 January 2025 #


import sys, os, base64, logging
from slowapi import App, Request, Response, FileResponse


class BasicAuthentication(App):
    def __init__(self, realm='SlowAPI', auth_list=[]):
        super().__init__()
        
        self.realm = realm

        self.auth_list = {}
        for auth in auth_list:
            try:
                (user, key) = tuple(auth.split(':', 1))
            except:
                logging.error('Bad authentication entry: %s' % auth)
                continue
            self.auth_list[user] = key
        
        if len(self.auth_list) > 0:
            try:
                global bcrypt
                import bcrypt
            except:
                logging.critical('SlowAPI_BasicAuthentication: missing python module "bcrypt"')
                sys.exit(-1)
        

    def require_auth(self, request:Request) -> Response:
        request.abort()
        response = Response(401)   # Unauthorized
        response.headers['WWW-Authenticate'] = f'Basic realm="{self.realm}"'
        return response
    
        
    def slowapi(self, request:Request, body:bytes=None) -> Response:
        if self.auth_list is None:
            return Response()

        auth = request.headers.get('Authorization', None)        
        if auth == '' or auth is None:
            return self.require_auth(request)

        try:
            user, word = tuple(base64.b64decode(auth.split(' ')[1]).decode().split(':'))
            true_key = self.auth_list.get(user, None)
            if word is None or true_key is None:
                return self.require_auth(request)
            
            key = bcrypt.hashpw(word.encode("utf-8"), true_key.encode()).decode("utf-8")
            if key == true_key:    # key is hashed and this is safe against timing attack
                request.user = user
                return Response()
        except Exception as e:
            logging.warning(f'SlowAPI_BasicAuthentication: Authentication Error: {str(e)}')
            
        return self.require_auth(request)


    @staticmethod
    def generate_key(user:str, word:str) -> str:
        import bcrypt
        return user + ':' + bcrypt.hashpw(word.encode(), bcrypt.gensalt(rounds=12, prefix=b"2a")).decode()
        



class FileServer(App):
    def __init__(self, filedir, *, basepath="", basepath_exclude=None, ext_allow=None, ext_deny=None, drop_basepath=False, index_file=None):
        """File Server App (Middleware)
        Args:
          - filedir (str): path to a filesystem directory
          - basepath (str): URL path to bind this app (e.g., "/webfile")
          - basepath_exclude (str): URL path not to use (e.g., basepath="/", basepath_exclude="/api")
          - ext_allow (list[str]): a list of file extensions to allow accessing
          - ext_deny (list[str]): a list of file extensions not to allow accessing
          - drop_basepath (bool): if True, the basepath is droppped from the path in the request
        Note:
          - file/dir names are restricted to:
            - start with an alphabet or digit
            - consist of only alphabets, digits, and selected special characters (_, -, +, ., =, ',', ':')
        """
        super().__init__()

        self.filedir = filedir
        self.basepath = None
        self.index_file = index_file
        self.basepath_exclude = None
        self.ext_allow = ext_allow
        self.ext_deny = ext_deny
        self.drop_basepath = drop_basepath
        self.stop_request_propagation = False

        if basepath is not None:
            self.basepath = [ p for p in basepath.split('/') if len(p) > 0 ]
        if basepath_exclude is not None:
            self.basepath_exclude = [ p for p in basepath_exclude.split('/') if len(p) > 0 ]

        
    def slowapi(self, request:Request, body:bytes=None) -> Response:
        # responds only to 'GET' requests
        if request.method != 'GET':
            return Response()
            
        # sanity check
        path = []
        is_dirty = False
        for p in request.path:
            if len(p) == 0:
                continue
            if not p[0].isalnum():
                is_dirty = True
            if not p.replace('_','a').replace('-','a').replace('+','a').replace('.','a').replace('=','a').replace(',','a').replace(':','a').isalnum():
                is_dirty = True
            path.append(p)
                
        # exclude path match
        if self.basepath_exclude is not None:
            if len(path) >= len(self.basepath_exclude):
                for i,p in enumerate(self.basepath_exclude):
                    if path[i] != p:
                        break
                else:
                    # match to exclusion                    
                    request.path = path[len(self.basepath_exclude):]
                    return Response()  

        # path match
        if self.basepath is not None:
            if len(path) < len(self.basepath):
                # no match -> propagate
                return Response()
            else:
                for i,p in enumerate(self.basepath):
                    if path[i] != p:
                        # no match -> propagate
                        return Response()

        # matched
        if self.stop_request_propagation:
            request.abort()            
        if is_dirty:
            return Response(403)  # Forbidden

        path = path[len(self.basepath):]
        if len(path) == 0:
            if self.index_file is not None:
                path = [ self.index_file ]
            else:
                return Response(403)  # Forbidden
        
        # file extension check
        ext = os.path.splitext(path[-1])[1]
        if self.ext_allow is not None:
            if ext not in self.ext_allow:
                return Response(403)  # Forbidden
        elif self.ext_deny is not None:
            if ext in self.ext_deny:
                return Response(403)  # Forbidden

        filepath = os.path.join(self.filedir, *(path[len(self.basepath):]))
        logging.debug(f'SlowAPI_FileServer: file request: {filepath}')

        return FileResponse(filepath)
