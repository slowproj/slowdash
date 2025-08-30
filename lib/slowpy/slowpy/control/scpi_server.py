# Created by Sanshiro Enomoto on 17 May 2024 #


import sys, time, os, subprocess, threading, signal, traceback
import socket, selectors
from slowpy.control import ControlSystem


class ScpiAdapter:
    def __init__(self, idn='Slow SCPI Device', **kwargs):
        self.idn = idn
        self.bound_nodes = []
        
        self.is_running = False
        self.errors = []


    def bind_nodes(self, nodelist):
        # nodelist: array of tuples of (path, node)
        for path, node in nodelist:
            cmds = []
            for p in path.split(':'):
                cmd = ''
                for ch in p:
                    if ch.islower():
                        break
                    cmd += ch
                if len(cmd) == 0:
                    cmd = p.upper()
                cmds.append(cmd)
            self.bound_nodes.append((cmds, node))


    # to be used internally or by subclasses
    def push_error(self, error):
        self.errors.append(error)


    # to be used internally
    def _process_node_command(self, command, params):
        target_node = None
        for name_path, node in self.bound_nodes:
            if len(name_path) != len(command):
                continue
            for k in range(len(name_path)):
                if not command[k].startswith(name_path[k]):
                    break
            else:
                target_node = node
                break

        if target_node is None:
            return None
                
        try:
            if command[-1][-1] == '?':
                value = node.get()
                return str(value) if value is not None else ''
            else:
                node.set(' '.join(params))
                return ''
        except Exception as e:
            print('ERROR: %s' % str(e))
            self.push_error('command error: %s: %s' % (str(e), ':'.join(command)))
            return ''

    
    ### Override the methods below as needed ###
        
    def do_RST(self):
        self.is_running = False
        self.errors = []
        return ''

    
    def do_CLS(self):
        self.errors = []
        return ''

    
    def do_OPC(self):
        return '1' if self.is_running else '0'

    
    def do_command(self, command, params):
        # command is a array, not empty, all in upper case
        # params is a array, can be empty
        # reutrn a reply text (even empty), or None if the command is not recognized
        return None

    
    def process_command(self, command, params):
        # device specific SCPI commands
        reply = self.do_command(command, params)
        if reply is not None:
            return reply
        
        # common SCPI commands
        if command[0] == '*IDN?':
            return self.idn
        elif command[0] == '*RST':
            return self.do_RST() or ''
        elif command[0] == '*CLS':
            return self.do_CLS() or ''
        elif command[0] == '*OPC?':
            return self.do_OPC()

        # SYSTem:ERRor? to get error messages
        elif len(command) > 1 and command[0].startswith('SYST'):
            if command[1].startswith('ERR') and command[1].endswith('?'):
                return self.errors.pop() if len(self.errors) > 0 else ''

        # SlowPy Control-Node commands
        else:
            reply = self._process_node_command(command, params)
            if reply is not None:
                return reply

        print('ERROR: invalid command: %s' % ':'.join(command))
        self.push_error('invalid command: %s' % ':'.join(command))
        
        return ''


        
class ScpiConnection(threading.Thread):
    def __init__(self, scpi_adapter, sock, addr, line_terminator):
        super().__init__()
        self.scpi_adapter = scpi_adapter
        self.sock = sock
        self.addr = addr
        self.line_terminator = line_terminator

        self.stop_event = threading.Event()
        self.selectors = selectors.DefaultSelector()
        self.selectors.register(self.sock, selectors.EVENT_READ)

        
    def stop(self):
        self.stop_event.set()
        del self.selectors

        
    def run(self):
        line = []
        while True:
            events = self.selectors.select(timeout=0.1)
            for key, mask in events:
                if key.fileobj == self.sock and mask != 0:
                    break
            else:
                if self.stop_event.is_set():
                    break
                else:
                    continue
            
            packet = self.sock.recv(1024)
            if len(packet) == 0 or self.stop_event.is_set():
                break

            for ch in packet:
                if ch != ord(self.line_terminator):
                    if ch not in [ ord('\x0a'), ord('\x0d') ]:
                        line.append(ch)
                else:
                    reply = self.process_command(bytes(line).decode('utf-8'))
                    try:
                        self.sock.sendall((reply+self.line_terminator).encode('utf-8'))
                    except:
                        break
                    line.clear()
                    
        self.sock.close()
        print("connection closed")

        
    def process_command(self, command):
        replies = []
        cmd_path = []
        for cmd in command.split(';'):
            split = cmd.strip().upper().split()
            if len(split) == 0 or len(split[0]) == 0:
                continue
            this_cmd_path, params = split[0], ' '.join(split[1:])
            
            if this_cmd_path.startswith(':'):
                cmd_path = this_cmd_path[1:].split(':')
            else:
                cmd_path = cmd_path[:-1] + this_cmd_path.split(':')
            cmd_path = [ node.strip() for node in cmd_path ]
            params = [ node.strip() for node in params.split(',') ]

            try:
                reply = self.scpi_adapter.process_command(cmd_path, params)
            except Exception as e:
                print('ERROR: %s' % str(e))
                print(traceback.format_exc())
            print("scpi: [%s] -> [%s]" % (cmd.strip(), reply))
            if cmd_path[-1][-1] == '?':
                replies.append(str(reply) if reply is not None else '')

        return ';'.join(replies)

    

class ScpiServer:
    def __init__(self, scpi_adapter, port, line_terminator='\x0d'):
        self.scpi_adapter = scpi_adapter
        self.line_terminator = line_terminator
        
        self.host = subprocess.check_output("hostname -I | cut -d' ' -f1", shell=True).decode('utf-8').splitlines()[0]
        self.port = port
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # allow immediate re-bind even during TIME_WAIT
        self.sock.bind((self.host, port))
        self.sock.listen(10)
        self.connections = []

        
    def start(self):
        def signal_handler(signum, frame):
            raise InterruptedError
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
            
        print("listening at %s:%d" % (self.host, self.port))
        print("line terminator is: x%02x" % ord(self.line_terminator))
        print("type Ctrl-c to stop")
        try:
            while True:
                sock, addr = self.sock.accept()
                conn = ScpiConnection(self.scpi_adapter, sock, addr, self.line_terminator)
                print("connection accepted")
                conn.start()
                self.connections.append(conn)
        except InterruptedError:
            print('terminating...')

        ControlSystem.stop()

        for conn in self.connections:
            conn.stop()
            conn.join()
        self.sock.close()
        print("server closed")
