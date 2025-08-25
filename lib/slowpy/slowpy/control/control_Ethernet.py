# Created by Sanshiro Enomoto on 17 May 2024 #


import sys, socket, selectors, time, threading, logging
import slowpy.control as spc


class EthernetNode(spc.ControlNode):
    def __init__(self, address, port, **kwargs):        
        self.address = address
        self.port = port
        self.reconnect_time = kwargs.get('reconnect', 10)
        self.terminator = None
        
        self.socket = None
        self.selectors = None
        self.lock = threading.Lock()
        
        self.last_connect_time = 0
        self.socket_buffer = ''
        
        if self.address is None or not int(self.port) > 0:
            logging.error(f'bad address or port: {self.address}:{self.port}')
            
            
    def __del__(self):
        if self.socket is not None:
            try:
                self.socket.close()
            except:
                pass
        del self.selectors
        
        
    def do_connect(self):
        if self.address is None or not int(self.port) > 0:
            return False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            del self.selectors
            del self.socket
            
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        try:
            self.socket.connect((self.address, self.port))
            logging.info(f'Ethernet: {self.address}:{self.port} connected')
        except Exception as e:
            logging.error(f'unable to connect to {self.address}:{self.port}: {e}')
            self.socket = None
            self.selectors = None
            return False

        self.selectors = selectors.DefaultSelector()
        self.selectors.register(self.socket, selectors.EVENT_READ)
        
        return True


    def is_available(self):
        if self.socket:
            return True
        if self.last_connect_time > 0 and not (self.reconnect_time > 0):
            return False
        
        now = time.monotonic()
        if now - self.last_connect_time < self.reconnect_time:
            return False
        self.last_connect_time = now
            
        return self.do_connect()
        
    
    def set(self, value):
        if self.is_available():
            try:
                self.socket.sendall(value.encode('utf-8'))
            except Exception as e:
                logging.warn(f'socket error: {e}')
                try:
                    self.socket.close()
                except:
                    pass
                self.socket = None

    
    def get(self):
        return self.do_get_chunk(timeout=None)


    ## methods ##    
    def do_get_chunk(self, timeout=None):
        """
        return value:
          - received chunk, can be empty if timeout occurs
          - None if socket is closed
        """
        
        if not self.is_available():
            return ''
    
        events = self.selectors.select(timeout=timeout)
        for key, mask in events:
            if key.fileobj == self.socket and mask != 0:
                try:
                    recv = self.socket.recv(1024*1024).decode('utf-8', errors='ignore')
                except Exception as e:
                    recv = ''
                    logging.warn(f'socket error: {e}')
                if len(recv) == 0: # EOF
                    logging.warn('socket disconnected')
                    try:
                        self.socket.close()
                    except:
                        pass
                    self.socket = None
                    return None
                else:
                    return recv
        else:
            return ''


    def do_get_line(self, timeout=None):
        """
        return value:
          - received line, without including line terminator (can be empty line)
          - None if timeout occurs
        """
        
        if not self.is_available():
            return None

        if timeout is not None:
            wait_until = time.monotonic() + timeout
        else:
            wait_until = None
        
        line = ''
        with self.lock:
            while True:
                if len(self.socket_buffer) == 0:
                    if self.is_stop_requested():
                        chunk = None
                    else:
                        chunk = self.do_get_chunk(timeout=0.1)
                    if chunk is None:  # stop requested or connection closed
                        if len(line) > 0:
                            break
                        else:
                            return None
                    self.socket_buffer = chunk
                
                if len(self.socket_buffer) == 0:
                    if wait_until is not None and time.monotonic() >= wait_until:
                        if len(line) > 0:
                            return line
                        else:
                            logging.debug('do_get_line(): socket timeout')
                            return None
                    else:
                        continue

                for k in range(len(self.socket_buffer)):
                    ch = self.socket_buffer[k]
                    if ch in [ '\x0a', '\x0d' ]:
                        if self.terminator is None:
                            self.terminator = ch
                        if ch == self.terminator:
                            self.socket_buffer = self.socket_buffer[k+1:]
                            return line
                        else:
                            # skip <CR> and <LF>
                            pass
                    else:
                        line += ch
                        
                self.socket_buffer = ''

        return line


    def do_flush_input(self):
        while not self.is_stop_requested():
            text = self.do_get_chunk(timeout=0.01) or ''
            if len(text) == 0:
                break
            logging.debug(f"dumping [{text.strip()}]")
    

    ## child nodes ##
    def scpi(self, **kwargs):
        return ScpiNode(self, **kwargs)
    

    def telnet(self, prompt, line_terminator, **kwargs):
        return TelnetNode(self, prompt, line_terminator, **kwargs)
    

    @classmethod
    def _node_creator_method(cls):
        def ethernet(self, address, port):
            name = '%s:%s' % (address, str(port))
            try:
                self._ethernet_nodes.keys()
            except:
                self._ethernet_nodes = {}
            node = self._ethernet_nodes.get(name, None)
        
            if node is None:
                node = EthernetNode(address, port)
                self._ethernet_nodes[name] = node

            return node

        return ethernet

    
    
class ScpiNode(spc.ControlNode):
    """Node for a SCPI device (typically one physical equipment that has one IP address)"""
    
    def __init__(self, connection, timeout=10, line_terminator='\x0d', sync=False, append_opc=False, verbose=False):
        """
        Parameters:
          - connection: instance of EthernetNode, SerialNode, etc
          - timeout: timeout
          - line_terminator: '\x0d' for CR, '\x0a' for NL
          - sync: if True, SCPI read is appended to SCPI write in ScpiCommand.set()
          - appdn_opc: if True, ';*OPC?' is appended to all SCPI commands
          - verbose: primt SCPI exchanges to sys.stderr
        """
        self.connection = connection
        self.timeout = timeout
        self.line_terminator = line_terminator
        self.sync = sync
        self.append_opc = append_opc
        self.verbose = verbose
        
        while len(self.connection.do_get_chunk(timeout=0.1) or '') > 0:
            pass

    
    def set(self, value):
        if self.verbose:
            sys.stderr.write('SCPI SET: [%s]' % value)
        return self.connection.set(value + self.line_terminator)
            
    
    def get(self):
        reply = self.connection.do_get_line(timeout=self.timeout)
        if self.verbose:
            sys.stderr.write(' --> [%s]\n' % reply)
        return reply


    ## child nodes ##
    def command(self, name, **kwargs):
        return ScpiCommandNode(self, name, **kwargs)

    

class ScpiCommandNode(spc.ControlVariableNode):
    def __init__(self, scpi, name, set_format=None):
        self.scpi = scpi
        self.name = name
        self.set_format = set_format
        
    
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

        if self.scpi.append_opc:
            cmd += ';*opc?'
                
        self.scpi.set(cmd)
                
        if self.scpi.sync:
            return self.scpi.get()

    
    def get(self):
        if self.name[-1] == '?':
            cmd = self.name
        else:
            cmd = f'{self.name}?'
            
        self.scpi.set(cmd)
        
        return self.scpi.get()

    

class TelnetNode(spc.ControlNode):
    def __init__(self, connection, prompt, line_terminator, timeout=10, has_echo=True):
        self.connection = connection
        self.prompt = prompt
        self.timeout = timeout
        self.has_echo = has_echo
        self.line_terminator = line_terminator

        while len(self.connection.do_get_chunk(timeout=0.1) or '') > 0:
            pass

        
    def set(self, value):
        self.connection.set(value + self.line_terminator)
        if self.has_echo:
            return self.connection.do_get_line() or ''            

    
    def get(self):
        if self.prompt is not None:
            return '\n'.join(self.do_get_lines_to_prompt())
        else:
            return self.connection.do_get_line(timeout=self.timeout)
            
        
    ## methods ##
    def do_get_lines_to_prompt(self, timeout=None):
        lines = []
        wait_until = time.monotonic() + (timeout or self.timeout or 10)
        
        while not self.is_stop_requested():
            line = self.connection.do_get_line(timeout=0.1)
            if line is None:
                if time.monotonic() >= wait_until:
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
    


class TelnetCommandNode(spc.ControlVariableNode):
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
