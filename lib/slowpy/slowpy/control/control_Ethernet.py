
from slowpy.control import ControlNode
import socket, selectors


class EthernetNode(ControlNode):
    def __init__(self, host, port, **kwargs):
        import socket
        self.host = host
        self.port = port
        self.line_terminator = kwargs.get('line_terminator') or '\x0d'
        self.dump_initial = kwargs.get('dump_initial', False)
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))
        self.socket_buffer = ''
        self.selectors = selectors.DefaultSelector()
        self.selectors.register(self.socket, selectors.EVENT_READ)
        print('Ethernet: %s:%s connected' % (host, str(port)))

    
    def __del__(self):
        self.socket.close()
        del self.selectors

        
    def set(self, value):
        self.socket.sendall((value+self.line_terminator).encode('utf-8'))

    
    def get(self):
        if self.dump_initial:
            self.dump_initial = False
            #TODO: implement timeout here
            print(f'Ethernet: initial dump: {self.get()}')
            
        line = ''
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
                    
                self.socket_buffer = self.socket.recv(1024).decode('utf-8')
                if len(self.socket_buffer) == 0:
                    break

            for k in range(len(self.socket_buffer)):
                ch = self.socket_buffer[k]
                if ch not in [ '\x0a', '\x0d' ]:
                    line += ch
                else:
                    if len(line) > 0:
                        self.socket_buffer = self.socket_buffer[k+1:]
                        return line
            self.socket_buffer = ''
                
        return line


    ## child nodes ##
    def scpi(self, base_name, **kwargs):
        try:
            self.scpi_nodes.keys()
        except:
            self.scpi_nodes = {}
        if base_name not in self.scpi_nodes:
            self.scpi_nodes[base_name] = ScpiNode(self, base_name, **kwargs)
            
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
    def __init__(self, connection, base_name, set_format=None):
        self.connection = connection
        self.base_name = base_name
        self.set_format = set_format
        
    
    def set(self, value):
        if self.set_format is None:
            self.connection.set('%s %s' % (self.base_name, str(value)))
        else:
            self.connection.set(self.set_format.format(value))
        self.connection.get()

    
    def get(self):
        self.connection.set('%s?' % self.base_name)
        return self.connection.get()


    
def export():
    return [ EthernetNode ]
