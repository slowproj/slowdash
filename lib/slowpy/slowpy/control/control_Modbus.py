# Created by Sanshiro Enomoto on 7 May 2025 #


import time, logging
from slowpy.control import ControlNode, ControlVariableNode, ControlException


class ModbusNode(ControlNode):
    def __init__(self, host:str, port:int=502):
        self.host = host
        self.port = port
        
        self.client = None
        self.retry_wait = 10
        self.last_retry_time = 0
        

    def __del__(self):
        self.close()

        
    def open(self):
        if self.client is not None:
            return True

        now = time.monotonic()
        if now - self.last_retry_time < self.retry_wait:
            return False
        self.last_retry_time = now
        
        try:
            from pymodbus.client import ModbusTcpClient
        except Exception:
            logging.error(f'unable to import pymodbus')
            return False
            
        try:
            self.client = ModbusTcpClient(self.host, port=self.port)
            if self.client.connect():
                print(f'Modbus Connected at {self.host}:{self.port}')
            else:
                logging.error(f'Modbus Intialization Error at {self.host}:{self.port}: connect() failed')
                self.client = None
        except Exception as e:
            logging.error(f'Modbus Intialization Error at {self.host}:{self.port}: {e}')
            self.client = None

        return self.client is not None
    
            
    def close(self):
        if self.client is not None:
            self.client.close()
            self.client = None

            
    ## child nodes ##
    # modbus().register(address)
    def register(self, address:int):
        return HoldingRegisterNode(self, address)

    
    # modbus().register32(address)
    def register32(self, address:int):
        return HoldingRegisterNode(self, address, words=2)

    
    # modbus().holding_register(address): this is same as modbus().register(address)
    def holding_register(self, address:int):
        return HoldingRegisterNode(self, address)

    
    # modbus().input_register(address)
    def input_register(self, address:int):
        return InputRegisterNode(self, address)

    
    @classmethod
    def _node_creator_method(cls):
        def modbus(self, host:str, port:int=502):
            if True:  # create a new connection everytime (othwerwise task stop/start will use the same connection)
                return ModbusNode(host, port)
            
            name = '%s:%s' % (host, str(port))
            try:
                self._modbus_nodes.keys()
            except:
                self._modbus_nodes = {}
            node = self._modbus_nodes.get(name, None)
        
            if node is None:
                node = ModbusNode(host, port)
                self._modbus_nodes[name] = node

            return node

        return modbus

    
    
class HoldingRegisterNode(ControlVariableNode):
    def __init__(self, modbus_node, address:int, words:int=1):
        self.modbus_node = modbus_node
        self.address = address
        self.words = words

        
    def set(self, value):
        if not self.modbus_node.open():
            return None

        try:
            if self.words == 1:
                data = value & 0xffff
                reply = self.modbus_node.client.write_register(self.address, data)
            else:
                data = [ (value >> (w * 16)) & 0xffff for w in reversed(range(self.words)) ]
                reply = self.modbus_node.client.write_registers(self.address, data)
        except Exception as e:
            logging.error(f'Modbus Error: write_register[s]: address {self.address}: {e}')
            self.modbus_node.close()  # this will start retrying
            return None
            
        if reply.isError():
            raise ControlException(f'Modbus Error Reply: write_register[s]: address={self.address}')

        
    def get(self):
        if not self.modbus_node.open():
            return None
        
        try:
            reply = self.modbus_node.client.read_holding_registers(self.address, count=self.words)
        except Exception as e:
            logging.error(f'Modbus Error: read_holding_registers(): {e}')
            self.modbus_node.close()  # this will start retrying
            return None

        if reply.isError():
            raise ControlException(f'Modbus Error Reply: read_holding_register(): address={self.address}')

        if self.words == 1:
            return reply.registers[0]
        else:
            value = 0
            for w in range(self.words):
                value = (value << 16) | reply.registers[w]
            return value

    

class InputRegisterNode(ControlVariableNode):
    def __init__(self, modbus_node, address:int):
        self.modbus_node = modbus_node
        self.address = address

        
    def get(self):
        if not self.modbus_node.open():
            return None
        
        try:
            reply = self.modbus_node.client.read_input_registers(self.address, count=1)
        except Exception as e:
            logging.error(f'Modbus Error: read_input_registers(): {e}')
            self.modbus_node.close()  # this will start retrying
            return None

        if reply.isError():
            raise ControlException(f'Modbus Error Reply: read_input_registers: address={self.address}')

        return reply.registers[0]
