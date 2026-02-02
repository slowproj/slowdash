# Created by Sanshiro Enomoto on 7 May 2025 #


import slowpy.control as spc
import logging


class ModbusNode(spc.ControlNode):
    def __init__(self, host:str, port:int=502):
        from pymodbus.client import ModbusTcpClient
        self.client = ModbusTcpClient(host, port=port)
        try:
            self.client.connect()
            print(f'Modbus Connected at {host}:{port}')
        except Exception as e:
            logging.error(f'Modbus Intialization Error at {host}:{port}: {e}')
            self.client = None

            
    ## child nodes ##
    # modbus().register(address)
    def register(self, address:int):
        return ModbusHoldingRegisterNode(self.client, address)

    
    # modbus().register32(address)
    def register32(self, address:int):
        return ModbusHoldingRegisterNode(self.client, address, words=2)

    
    # modbus().holding_register(address): this is same as modbus().register(address)
    def holding_register(self, address:int):
        return ModbusHoldingRegisterNode(self.client, address)

    
    # modbus().input_register(address)
    def input_register(self, address:int):
        return ModbusInputRegisterNode(self.client, address)

    
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

    
    
class ModbusHoldingRegisterNode(spc.ControlVariableNode):
    def __init__(self, modbus, address:int, words:int=1):
        self.modbus = modbus
        self.address = address
        self.words = words

        
    def set(self, value):
        if self.modbus is None:
            return None

        if self.words == 1:
            self.modbus.write_register(self.address, value)
        else:
            data = [ (value >> (w * 16)) & 0xffff for w in reversed(range(self.words)) ]
            self.modbus.write_registers(self.address, data)
            
        
    def get(self):
        if self.modbus is None:
            return None
        
        try:
            reply = self.modbus.read_holding_registers(self.address, count=self.words)
            if reply.isError():
                raise Exception(f'address: {self.address}')
        except Exception as e:
            logging.error(f'Modbus Error: read_holding_registers(): {e}')
            return None

        if self.words == 1:
            return reply.registers[0]
        else:
            value = 0
            for w in range(self.words):
                value = (value << 16) | reply.registers[w]
            return value

    

class ModbusInputRegisterNode(spc.ControlVariableNode):
    def __init__(self, modbus, address:int):
        self.modbus = modbus
        self.address = address

        
    def get(self):
        if self.modbus is None:
            return None
        
        try:
            reply = self.modbus.read_input_registers(self.address)
            if reply.isError():
                raise Exception(f'address: {self.address}')
        except Exception as e:
            logging.error(f'Modbus Error: read_input_registers(): {e}')
            return None

        return reply.registers[0]
