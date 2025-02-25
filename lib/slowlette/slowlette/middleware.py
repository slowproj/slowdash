# Created by Sanshiro Enomoto on 18 January 2025 #


import sys, os, base64, logging

from .request import Request
from .response import Response, FileResponse
from .router import route


class BasicAuthentication():
    def __init__(self, realm='Slowlette', auth_list=[]):
        self.realm = realm

        self.auth_list = {}
        for auth in auth_list:
            try:
                (user, key) = tuple(auth.split(':', 1))
            except:
                # auth is already encrypted
                logging.error('Bad authentication entry: %s' % auth)
                continue
            self.auth_list[user] = key
        
        if len(self.auth_list) > 0:
            try:
                global bcrypt
                import bcrypt
            except:
                logging.critical('Slowlette_BasicAuthentication: missing python module "bcrypt"')
                sys.exit(-1)
        

    def require_auth(self, request:Request) -> Response:
        request.abort()
        response = Response(401)   # Unauthorized
        response.headers['WWW-Authenticate'] = f'Basic realm="{self.realm}"'
        return response
    
        
    @route('/{*}')
    def dispatch(self, request:Request, body:bytes=None) -> Response:
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
            logging.warning(f'Slowlette_BasicAuthentication: Authentication Error: {str(e)}')
            
        return self.require_auth(request)


    @staticmethod
    def generate_key(username:str, password:str) -> str:
        import bcrypt
        return username + ':' + bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12, prefix=b"2a")).decode()
        


class FileServer():
    def __init__(self, filedir, *, prefix="", index_file=None, exclude=None, drop_exclude_prefix=False, ext_allow=None, ext_deny=None):
        """File Server App (Middleware)
        Args:
          - filedir (str): path to a filesystem directory
          - prefix (str): URL path to bind this app (e.g., "/webfile")
          - index_file (str): index file when the path is empty (i.e., '/')
          - exclude (str): URL path not to be handled
            (e.g., prefix="/app", exclude="/app/api")
          - drop_exclude_prefix (bool): if True, the prefix is removed from the requet path if the request is for an excluded path
            (e.g., for exclude '/api', the request path of '/api/userlist' becomes '/userlist')
          - ext_allow (list[str]): a list of file extensions to allow accessing
          - ext_deny (list[str]): a list of file extensions not to allow accessing
        Note:
          - file/dir names are restricted to:
            - start with an alphabet or digit
            - consist of only alphabets, digits, and selected special characters (_, -, +, ., =, ',', ':')
        """

        self.filedir = filedir
        self.prefix = None
        self.index_file = index_file
        self.exclude = None
        self.ext_allow = ext_allow
        self.ext_deny = ext_deny
        self.drop_exclude_prefix = drop_exclude_prefix
        self.stop_request_propagation = True

        if prefix is not None:
            self.prefix = [ p for p in prefix.split('/') if len(p) > 0 ]
        if exclude is not None:
            self.exclude = [ p for p in exclude.split('/') if len(p) > 0 ]


    @route('/{*}')
    async def dispatch(self, request:Request, body:bytes=None) -> Response:
        # sanity check
        path = []
        is_dirty = False
        for p in request.path:
            if len(p) == 0:
                continue
            if not p[0].isalnum():
                is_dirty = True
            if not p.replace('_','').replace('-','').replace('+','').replace('=','').replace('.','').replace(',','').replace(':','').isalnum():
                is_dirty = True
            path.append(p)
        # exclude-path match
        if self.exclude is not None:
            if len(path) >= len(self.exclude):
                for i,p in enumerate(self.exclude):
                    if path[i] != p:
                        break
                else:
                    # match to exclusion
                    if self.drop_exclude_prefix:
                        request.path = path[len(self.exclude):]
                    return Response()  

        # method match
        # We apply URL rewriting even for non-GET methods (like POST api/command -> /command),
        # so this method check must be after the exclusion match.
        if request.method != 'GET':
            return Response()  # propagate
        
        # path match
        if self.prefix is not None:
            if len(path) < len(self.prefix):
                # no match -> propagate
                return Response()
            else:
                for i,p in enumerate(self.prefix):
                    if path[i] != p:
                        # no match -> propagate
                        return Response()
            path = path[len(self.prefix):]

        # matched -> my responsibility (can return an error status) #
        
        if self.stop_request_propagation:
            request.abort()            
        if is_dirty:
            return Response(403)  # Forbidden
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

        filepath = os.path.join(*(path))
        if len(os.path.splitdrive(filepath)[0]) > 0:  # Windows drive letter :-(
            return Response(403)  # Forbidden
                
        filepath = os.path.join(self.filedir, filepath)
        logging.debug(f'Slowlette_FileServer: file request: {filepath}')

        return await FileResponse().load(filepath)

