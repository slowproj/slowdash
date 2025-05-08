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
    # modbus().holding_register(address)
    def holding_register(self, address:int):
        return ModbusHoldingRegisterNode(self.client, address)

    
    # modbus().input_register(address)
    def input_register(self, address:int):
        return ModbusInputRegisterNode(self.client, address)

    
    @classmethod
    def _node_creator_method(cls):
        def modbus(self, host:str, port:int=502):
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
    def __init__(self, modbus, address:int):
        self.modbus = modbus
        self.address = address

        
    def set(self, value):
        if self.modbus is None:
            return None
        
        self.modbus.write_register(self.address, value)

        
    def get(self):
        if self.modbus is None:
            return None
        
        try:
            reply = self.modbus.read_holding_registers(self.address)
        except Exception as e:
            logging.error(f'Modbus Error: read_holding_registers(): {e}')
            return None

        return reply.registers[0]

    

class ModbusInputRegisterNode(spc.ControlVariableNode):
    def __init__(self, modbus, address:int):
        self.modbus = modbus
        self.address = address

        
    def get(self):
        if self.modbus is None:
            return None
        
        try:
            reply = self.modbus.read_input_registers(self.address)
        except Exception as e:
            logging.error(f'Modbus Error: read_input_registers(): {e}')
            return None

        return reply.registers[0]
