
from slowpy.control import Endpoint


class EthernetEndpoint(Endpoint):
    def __init__(self, parent, host, port, **kwargs):
        import socket
        self.host = host
        self.port = port
        self.line_terminator = kwargs.get('line_terminator') or '\x0d'
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))
        self.socket_buffer = []
        print('Ethernet: %s:%s connected' % (host, str(port)))

    
    def __del__(self):
        self.socket.close()

        
    def set(self, value):
        self.socket.sendall((value+self.line_terminator).encode('utf-8'))

    
    def get(self):
        line = []
        while True:
            if len(self.socket_buffer) == 0:
                self.socket_buffer = self.socket.recv(1024)
            if len(self.socket_buffer) == 0:
                break

            while True:
                ch = self.socket_buffer[0]
                self.socket_buffer = self.socket_buffer[1:]
                if ch not in [ ord('\x0a'), ord('\x0d') ]:
                    line.append(ch)
                if (len(self.socket_buffer)) == 0 or (ch == ord(self.line_terminator)):
                    return bytes(line).decode('utf-8')
                
        return bytes(line).decode('utf-8')


    # This method can be injected dynamically by the method call below:
    #    EthernetEndpoint.add_endpoint(ScpiEndpoint, name="scpi")
    # As this endpoint is small, we just "hard-code" it.
    def scpi(self, base_name):
        return ScpiEndpoint(self, base_name)
    

    @classmethod
    def _endpoint_creator_method(cls):
        def ethernet(self, host, port):
            name = '%s:%s' % (host, str(port))
            try:
                self._ethernet_endpoints.keys()
            except:
                self._ethernet_endpoints = {}
            endpoint = self._ethernet_endpoints.get(name, None)
        
            if endpoint is None:
                endpoint = EthernetEndpoint(self, host, port)
                self._ethernet_endpoints[name] = endpoint

            return endpoint

        return ethernet

    
    
class ScpiEndpoint(Endpoint):
    def __init__(self, connection, base_name):
        self.connection = connection
        self.base_name = base_name
        
    
    def set(self, value):
        self.connection.set('%s %s' % (self.base_name, str(value)))
        self.connection.get()

    
    def get(self):
        self.connection.set('%s?' % self.base_name)
        return self.connection.get()


    
def export():
    return [ EthernetEndpoint ]
