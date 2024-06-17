# Created by Sanshiro Enomoto on 17 May 2024 #


import sys, time, os, subprocess, threading, signal
import socket, selectors


class SerialDevice:
    def __init__(self, **kwargs):
        self.line_terminator = kwargs.get('line_terminator') or '\x0d' #CR

        
    # override this
    def process_command(self, command):
        return ''

    
        
class ScpiDevice(SerialDevice):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        
    # override this
    def process_scpi_command(self, cmd_path, params):
        return ''

    
    def process_command(self, command):
        reply = ''
        
        cmd_path = []
        for cmd in command.split(';'):
            split = cmd.strip().split()
            if len(split) == 0 or len(split[0]) == 0:
                continue
            this_cmd_path, params = split[0], split[1:]
            
            if this_cmd_path.startswith(':'):
                cmd_path = this_cmd_path[1:].split(':')
            else:
                cmd_path = cmd_path[:-1] + this_cmd_path.split(':')
            cmd_path = [ node.upper().strip() for node in cmd_path ]
                
            reply = self.process_scpi_command(cmd_path, params)
            print("scpi: [%s] -> [%s]" % (cmd.strip(), reply))

        return reply

    
    
    
class SerialDeviceEthernetLink(threading.Thread):
    def __init__(self, serial_device, sock, addr):
        super().__init__()
        self.serial_device = serial_device
        self.sock = sock
        self.addr = addr
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
            
            packet = self.sock.recv(1024)
            if len(packet) == 0 or self.stop_event.is_set():
                break

            for ch in packet:
                if ch != ord(self.serial_device.line_terminator):
                    if ch not in [ ord('\x0a'), ord('\x0d') ]:
                        line.append(ch)
                else:
                    reply = self.serial_device.process_command(bytes(line).decode('utf-8'))
                    try:
                        self.sock.sendall((reply+self.serial_device.line_terminator).encode('utf-8'))
                    except:
                        break
                    line.clear()
                    
        self.sock.close()
        print("connection closed")

        

def signal_handler(signum, frame):
    raise InterruptedError



class SerialDeviceEthernetServer:
    def __init__(self, serial_device, port):
        self.serial_device = serial_device
        
        host = subprocess.check_output("hostname -I | cut -d' ' -f1", shell=True).decode('utf-8').splitlines()[0]
        #host = socket.gethostname()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((host, port))
        self.sock.listen(10)
        self.links = []
        print("listening at %s:%d" % (host, port))
        print("line terminator is: x%02x" % ord(self.serial_device.line_terminator))

        
    def start(self):
        try:
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            while True:
                sock, addr = self.sock.accept()
                link = SerialDeviceEthernetLink(self.serial_device, sock, addr)
                print("connection accepted")
                link.start()
                self.links.append(link)
        except InterruptedError:
            print('terminating...')

        for link in self.links:
            link.stop()
            link.join()
        self.sock.close()
