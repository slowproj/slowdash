
from slowpy.control import ControlNode
import socket, selectors, time


class EthernetNode(ControlNode):
    def __init__(self, host, port, **kwargs):
        import socket
        self.host = host
        self.port = port
        
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
            self.socket.sendall(value.encode('utf-8'))

    
    def get(self):
        return self.do_get_chunk(timeout=None)


    ## methods ##    
    def do_get_chunk(self, timeout=None):
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
                if wait_until is not None and time.time() >= wait_until:
                    if timeout > 1:
                        print('do_get_line(): socket timeout')
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
            print(f"dumping [{text.strip()}]")
    

    ## child nodes ##
    def scpi(self, **kwargs):
        return ScpiNode(self, **kwargs)
    

    def telnet(self, prompt, line_terminator, **kwargs):
        return TelnetNode(self, prompt, line_terminator, **kwargs)
    

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
    def __init__(self, connection, timeout=10, line_terminator='\x0d'):
        self.connection = connection
        self.timeout = timeout
        self.line_terminator = line_terminator
        
        while len(self.connection.do_get_chunk(timeout=0.1)) > 0:
            pass

    
    def set(self, value=None):
        return self.connection.set(value + self.line_terminator)
            
    
    def get(self):
        return self.connection.do_get_line(timeout=self.timeout)


    ## child nodes ##
    def command(self, name, **kwargs):
        return ScpiCommandNode(self, name, **kwargs)

    

class ScpiCommandNode(ControlValueNode):
    def __init__(self, scpi, name, set_format=None, sync=True):
        self.scpi = scpi
        self.name = name
        self.set_format = set_format
        self.sync = sync
        
    
    def set(self, value=None):
        if self.set_format is None:
            if value is None:
                cmd = self.name
            else:
                cmd = '%s %s' % (self.name, str(value))
        else:
            if value is None:
                cmd = self.set_format
            else:
                cmd = self.set_format.format(value)
                
        self.scpi.set(cmd)
                
        if self.sync:
            self.scpi.get()

    
    def get(self):
        if self.name[-1] == '?':
            cmd = self.name
        else:
            cmd = f'{self.name}?'
            
        self.scpi.set(cmd)
        
        return self.scpi.get()

    

class TelnetNode(ControlNode):
    def __init__(self, connection, prompt, line_terminator, timeout=10, has_echo=True):
        self.connection = connection
        self.prompt = prompt
        self.timeout = timeout
        self.has_echo = has_echo
        self.line_terminator = line_terminator

        while len(self.connection.do_get_chunk(timeout=0.1)) > 0:
            pass

        
    def set(self, value):
        self.connection.set(value + self.line_terminator)
        if self.has_echo:
            self.connection.do_get_line()

    
    def get(self):
        if self.prompt is not None:
            return '\n'.join(self.do_get_lines_to_prompt())
        else:
            return self.connection.do_get_line(timeout=self.timeout)
            
        
    ## methods ##
    def do_get_lines_to_prompt(self, timeout=None):
        lines = []
        wait_until = time.time() + (timeout or self.timeout or 10)
        
        while not self.is_stop_requested():
            line = self.connection.do_get_line(timeout=0.1)
            if len(line) == 0:
                if time.time() >= wait_until:
                    break
                else:
                    continue
            if line.startswith(self.prompt):
                break
            lines.append(line.strip())

        return lines
        
    
    ## child nodes ##
    def command(self, command, **kwargs):
        return TelnetCommandNode(self, command, **kwargs)
    


class TelnetCommandNode(ControlValueNode):
    def __init__(self, telnet, command):
        self.telnet = telnet
        self.command = command
        
    
    def set(self, value=None):
        if value is None:
            return self.telnet.set(self.command)
        else:
            return self.telnet.set(f'{self.command} {str(value)}')

    
    def get(self):
        self.telnet.set(self.command)
        return self.telnet.get()

    
   
def export():
    return [ EthernetNode ]
