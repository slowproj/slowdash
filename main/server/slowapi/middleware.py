# Created by Sanshiro Enomoto on 18 January 2025 #


import sys, base64, logging
from slowapi import App, Request, Response


class BasicAuthentication(App):
    def __init__(self, realm='SlowAPI', auth_list=[]):
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
            if key == true_key:
                request.user = user
                return Response()
        except Exception as e:
            logging.warning(f'SlowAPI_BasicAuthentication: Authentication Error: {str(e)}')
            
        return self.require_auth(request)


    @staticmethod
    def generate_key(user:str, word:str) -> str:
        import bcrypt
        return user + ':' + bcrypt.hashpw(word.encode(), bcrypt.gensalt(rounds=12, prefix=b"2a")).decode()
        
