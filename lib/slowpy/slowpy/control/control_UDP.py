# Created by Clint Wiseman on 23 April 2026 # 


import socket, selectors, threading, logging
import slowpy.control as spc


class UDPNode(spc.ControlNode):
    """Node for a UDP style connection (socket.SOCK_DGRAM)"""
    
    def __init__(self, port, address="0.0.0.0", timeout=1, **kwargs):        
        # In UDP, we usually bind to "0.0.0.0" to hear from all devices
        self._address = address 
        self._port = port
        self._socket = None
        self._selectors = None
        self._lock = threading.Lock()
        self._socket_buffer = ''
        self._terminator = None
        self._is_thread_safe = True
        self._timeout=timeout
    
        if self._address is None or not int(self._port) > 0:
            logging.error(f'bad address or port: {self._address}:{self._port}')            

    def __del__(self):
        self.close()
        
    def close(self):
        if self._socket is not None:
            self._socket.close()
        # del self._selectors
        self._selectors = None
        self._socket = None

    def open(self):
        if self._address is None or not int(self._port) > 0:
            return False
        if self._socket:
            try:
                self._socket.close()
            except:
                pass
            del self._selectors
            del self._socket
            
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.settimeout(self._timeout)
        
        # tell the OS to immediately reuse the port if it's lingering
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            logging.info(f'UDP: binding to {self._address}:{self._port} ...')
            self._socket.bind((self._address, self._port))
            logging.info(f'UDP: listening at {self._address}:{self._port}')
        except Exception as e:
            logging.error(f'Unable to bind {self._address}:{self._port}: {e}')
            self._socket = None
            self._selectors = None
            return False

        self._selectors = selectors.DefaultSelector()
        self._selectors.register(self._socket, selectors.EVENT_READ)

        return True
    
    def get(self):
        """To avoid timeouts & hangups calling socket.recvfrom directly, use selectors"""
        
        # # Simple version - can cause errors if the sender stops sending
        # data, addr = self._socket.recvfrom(1024)
        # addr = addr.decode(errors='ignore')
        # return data, addr
        
        if self._selectors is None or self._socket is None:
            if not self.open():
                return None, None

        # ask the selector if there is data waiting (will wait up to self._timeout seconds.)
        events = self._selectors.select(timeout=self._timeout)
        
        if not events:
            # No data arrived within the timeout period
            return None, None

        for key, mask in events:
            # ensure the socket is ready to be read
            if mask & selectors.EVENT_READ:
                try:
                    data, addr = self._socket.recvfrom(1024) # returns (bytes, (ip, port))
                    
                    # decode data to string, don't enforce an automatic type choice here
                    decoded_data = data.decode('utf-8', errors='ignore')
                    return decoded_data, addr
                except Exception as e:
                    logging.error(f"UDP Read Error: {e}")
                    return None, None
        return None, None
    
    def is_available(self):
        # UDP is always 'available' once bound
        return self._socket is not None or self.do_connect()
    
    def has_data(self):
        # Used to drain stale packets (buffer bloat).
        if self._selectors is None or self._socket is None:
            return False
            
        # timeout=0.0 makes this a non-blocking wait
        events = self._selectors.select(timeout=0.0)
        
        return len(events) > 0 # True if we have data
    
    @classmethod
    def _node_creator_method(cls):
        def udp(self, port, address=None):
            return UDPNode(port, address)
        return udp
