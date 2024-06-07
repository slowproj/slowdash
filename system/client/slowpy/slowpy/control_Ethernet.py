
from slowpy import ControlNode
import socket, selectors


class EthernetNode(ControlNode):
    def __init__(self, host, port, **kwargs):
        import socket
        self.host = host
        self.port = port
        self.line_terminator = kwargs.get('line_terminator') or '\x0d'
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))
        self.socket_buffer = []
        self.selectors = selectors.DefaultSelector()
        self.selectors.register(self.socket, selectors.EVENT_READ)
        print('Ethernet: %s:%s connected' % (host, str(port)))

    
    def __del__(self):
        self.socket.close()
        del self.selectors

        
    def set(self, value):
        self.socket.sendall((value+self.line_terminator).encode('utf-8'))

    
    def get(self):
        line = []
        while True:
            if len(self.socket_buffer) == 0:
                events = self.selectors.select(timeout=0.1)
                for key, mask in events:
                    if key.fileobj == self.socket and mask != 0:
                        break
                else:
                    if self.is_stop_requested():
                        break
                    else:
                        continue
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


    ## child nodes ##
    def scpi(self, base_name):
        try:
            self.scpi_nodes.keys()
        except:
            self.scpi_nodes = {}
        if base_name not in self.scpi_nodes:
            self.scpi_nodes[base_name] = ScpiNode(self, base_name)
            
        return self.scpi_nodes[base_name]
    

    @classmethod
    def _node_creator_method(cls):
        def ethernet(self, host, port):
            name = '%s:%s' % (host, str(port))
            try:
                self._ethernet_nodes.keys()
            except:
                self._ethernet_nodes = {}
            node = self._ethernet_nodes.get(name, None)
        
            if node is None:
                node = EthernetNode(host, port)
                self._ethernet_nodes[name] = node

            return node

        return ethernet

    
    
class ScpiNode(ControlNode):
    def __init__(self, connection, base_name):
        self.connection = connection
        self.base_name = base_name
        
    
    def set(self, value):
        self.connection.set('%s %s' % (self.base_name, str(value)))
        self.connection.get()

    
    def get(self):
        self.connection.set('%s?' % self.base_name)
        return self.connection.get()


    ## child nodes ##
    def with_opc_for_set(self):
        return ScpiWithOpcNode(self.connection, self.base_name)
    
    

class ScpiWithOpcNode(ControlNode):
    def __init__(self, connection, base_name):
        self.connection = connection
        self.base_name = base_name

        
    def set(self, value):
        self.connection.set('%s %s;OPC?' % (self.base_name, str(value)))
        self.connection.get()

    
    def get(self):
        self.connection.set('%s?' % self.base_name)
        return self.connection.get()

    

    
def export():
    return [ EthernetNode ]
