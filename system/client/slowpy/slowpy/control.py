

class Endpoint:
    def __init__(self):
        pass

    def set(self, value):
        pass

    def get(self):
        return None

    def __str__(self):
        return str(self.get())
    
    def __float__(self):
        return float(self.get())
    
    @classmethod
    def load(cls, module_name):
        pass

    

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



class EthernetEndpoint(Endpoint):
    def __init__(self, host, port, **kwargs):
        import socket
        self.host = host
        self.port = port
        
        self.line_terminator = kwargs.get('line_terminator') or '\x0a'
        self.socket_buffer = []
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))
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


    
    def scpi(self, base_name):
        return ScpiEndpoint(self, base_name)


    
        
class ControlSystem(Endpoint):
    def __init__(self):
        self.ethernet_endpoints = {}

    
    def ethernet(self, host, port):
        name = '%s:%s' % (host, str(port))
        try:
            self.ethernet_endpoints
        except:
            self.ethernet_endpoints = {}
        endpoint = self.ethernet_endpoints.get(name, None)
        
        if endpoint is None:
            endpoint = EthernetEndpoint(host, port)
            self.ethernet_endpoints[name] = endpoint

        return endpoint
