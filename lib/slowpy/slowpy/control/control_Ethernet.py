
from slowpy.control import ControlNode
import socket, selectors, time


class EthernetNode(ControlNode):
    def __init__(self, host, port, **kwargs):
        import socket
        self.host = host
        self.port = port
        self.line_terminator = kwargs.get('line_terminator') or '\x0d'
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_buffer = ''
        self.selectors = selectors.DefaultSelector()
        self.selectors.register(self.socket, selectors.EVENT_READ)

        try:
            self.socket.connect((self.host, self.port))
        except Exception as e:
            print('ERROR: Ethernet: unable to connect to %s:%s: %s' % (host, str(port), str(e)))
            del self.socket
            self.socket = None
        
        print('Ethernet: %s:%s connected' % (host, str(port)))
            
    
    def __del__(self):
        self.socket.close()
        del self.selectors

        
    def set(self, value):
        if self.socket:
            self.socket.sendall((value+self.line_terminator).encode('utf-8'))

    
    def get(self):
        return self.do_get_line()


    ## methods ##    
    def do_get_chunk(self, timeout=1.0):
        if self.socket is None:
            return None
    
        events = self.selectors.select(timeout=timeout)
        for key, mask in events:
            if key.fileobj == self.socket and mask != 0:
                return self.socket.recv(1024*1024).decode('utf-8', errors='ignore')
        else:
            return ''


    def do_get_line(self, timeout=None):
        if self.socket is None:
            return None

        if timeout is not None:
            wait_until = time.time() + timeout
        else:
            wait_until = None
        
        line = ''
        while not self.is_stop_requested():
            if len(self.socket_buffer) == 0:
                self.socket_buffer = self.do_get_chunk(timeout=0.1)
                
            if len(self.socket_buffer) == 0:
                if wait_until is not None and time.time() > wait_until:
                    break
                else:
                    continue

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


    def do_flush_input(self):
        while not self.is_stop_requested():
            text = self.do_get_chunk(timeout=0.01)
            if len(text) == 0:
                break
            #print(f"dumping [{text.strip()}]")
    

    ## child nodes ##
    def scpi(self, base_name, **kwargs):
        return ScpiNode(self, base_name, **kwargs)
    

    def telnet(self, command, **kwargs):
        return TelnetNode(self, command, **kwargs)
    

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
    def __init__(self, connection, base_name, set_format=None, sync=True, timeout=10):
        self.connection = connection
        self.base_name = base_name
        self.set_format = set_format
        self.sync = sync
        self.timeout = timeout
        
    
    def set(self, value=None):
        if self.set_format is None:
            if value is None:
                self.connection.set('%s' % self.base_name)
            else:
                self.connection.set('%s %s' % (self.base_name, str(value)))
        else:
            if value is None:
                self.connection.set(self.set_format)
            else:
                self.connection.set(self.set_format.format(value))

        if self.sync:
            self.connection.get()
            
    
    def get(self):
        if self.base_name[-1] == '?':
            self.connection.set('%s' % self.base_name)
        else:
            self.connection.set('%s?' % self.base_name)
        return self.connection.do_get_line(timeout=timeout)


    
class TelnetNode(ControlNode):
    def __init__(self, connection, command, prompt='>', timeout=10, has_echo=True):
        self.connection = connection
        self.command = command
        self.prompt = prompt
        self.timeout = timeout
        self.has_echo = has_echo
        
    
    def set(self, value=None):
        if value is None:
            cmd = self.command
        else:
            cmd = '%s %s' % (self.command, str(value))
            
        self.connection.do_flush_input()
        self.connection.set(cmd)
        self.do_get_lines_to_prompt()

    
    def get(self):
        self.connection.do_flush_input()
        self.connection.set(self.command)
        lines = self.do_get_lines_to_prompt()
        
        if self.has_echo and len(lines) > 0 and lines[0] == self.command:
            # TODO: check this is really the echo string
            lines = lines[1:]

        return '\n'.join(lines)
            
        
    def do_get_lines_to_prompt(self):
        lines = []
        wait_until = time.time() + (self.timeout or 10)
        
        while not self.is_stop_requested() and time.time() < wait_until:
            line = self.connection.do_get_line(timeout=0.1)
            if len(line) == 0:
                continue
            if line.startswith(self.prompt):
                break
            lines.append(line.strip())

        return lines
        
    
def export():
    return [ EthernetNode ]
