#! /usr/bin/env python3

import sys, time, os, subprocess, threading, socket, signal


class App(threading.Thread):
    def __init__(self):
        super().__init__()
        self.stop_event = threading.Event()
        self.terminator = '\x0a'

        
    def stop(self):
        self.stop_event.set()

        
    # override this
    def run(self):
        while not self.stop_event.is_set():
            time.sleep(1)

            
    # override this
    def process_query(self, query):
        return None

        
        
class Connection(threading.Thread):
    def __init__(self, app, sock, addr):
        super().__init__()
        self.app = app
        self.sock = sock
        self.addr = addr
        self.stop_event = threading.Event()

        
    def stop(self):
        self.stop_event.set()

        
    def run(self):
        buffer = []
        while True:
            # TODO: use select() to check the stop_event
            packet = self.sock.recv(1024)
            for ch in packet:
                if ch == ord(self.app.terminator):
                    query = bytes(buffer).decode('utf-8').strip()
                    if query == 'bye':
                        reply = ''
                        self.stop_event.set()
                    else:
                        for cmd in query.split(';'):
                            reply = self.app.process_query(cmd.strip())
                        if reply is None:
                            reply = 'ERROR'
                        self.sock.sendall((reply+self.app.terminator).encode('utf-8'))
                    buffer.clear()
                    print("query: [%s] -> [%s]" % (query, reply))
                elif ch != 0x0a:
                    buffer.append(ch)
            if len(packet) == 0 or self.stop_event.is_set():
                break
        self.sock.close()

        

def signal_handler(signum, frame):
    raise InterruptedError



class Server:
    def __init__(self, app, port):
        self.app = app
        
        host = subprocess.check_output("hostname -I | cut -d' ' -f1", shell=True).decode('utf-8').splitlines()[0]
        #host = socket.gethostname()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((host, port))
        self.sock.listen(10)
        self.connections = []
        print("listening at %d@%s" % (port, host))

        
    def start(self):
        self.app.start()
        try:
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            while True:
                sock, addr = self.sock.accept()
                conn = Connection(app, sock, addr)
                conn.start()
                self.connections.append(conn)
        except InterruptedError:
            print('terminating...')

        self.app.stop()
        self.app.join()
        for conn in self.connections:
            conn.stop()
            conn.join()
        self.sock.close()


        
import collections

def parse_args(argv):
    args = collections.namedtuple('args', ('params', 'opts'))
    args.params = []
    args.opts = collections.OrderedDict()
    
    for arg in argv[1:]:
        if arg == '--' or arg[0:2] != '--':
            args.params.append(arg)
            continue
        kv = arg[2:].split('=', 1)
        if len(kv) == 1:
            args.opts[kv[0]] = True
        else:
            args.opts[kv[0]] = kv[1]

    return args



#############################################################

import slowpy as slp


class DummyScpiApp(App):
    def __init__(self, opts={}):
        super().__init__()
        self.device = slp.DummyWalkDevice(n=4, walk=1.0, decay=0.1, wait=0)

        
    def run(self):
        while not self.stop_event.is_set():
            self.record = self.device.read()
            time.sleep(1)

            
    def process_query(self, query):
        split = query.upper().split()
        if len(split) < 2:
            key, params = query.upper(), ['']
        else:
            key, params = split[0], split[1:]
        path = key.split(':')
            
        if key == '*IDN?':
            return 'Dummy SCPI Device'
        elif key == '*OPC?':
            return '1'
        elif key == '*RST':
            self.device.walk = 1.0
            self.device.decay = 0.1
            return ''
        elif key == '*CLS':
            return ''

        elif path[0][0:4] == 'MEAS' and key == 'V0?':
            return '%f' % self.record[0]['value']
        elif path[0][0:4] == 'MEAS' and key == 'V1?':
            return '%f' % self.record[1]['value']
        elif path[0][0:4] == 'MEAS' and key == 'V2?':
            return '%f' % self.record[2]['value']
        elif path[0][0:4] == 'MEAS' and key == 'V3?':
            return '%f' % self.record[3]['value']

        elif key == 'WALK?':
            return '%f' % self.device.walk
        elif key == 'DECAY?':
            return '%f' % self.device.decay

        elif key == 'WALK' :
            try:
                self.device.walk = float(params[0])
                return '%f' % self.device.walk
            except:
                return None
        elif key == 'DECAY':
            try:
                self.device.decay = float(params[0])
                return '%f' % self.device.decay
            except:
                return None
            
        else:
            return None

        

if __name__ == '__main__':
    args = parse_args(sys.argv)
    port = int(args.opts.get("port", 17674))
    
    app = DummyScpiApp(args.opts)
    server = Server(app, port=port)
    server.start()
