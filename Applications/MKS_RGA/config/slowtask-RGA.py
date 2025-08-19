# control_MKS_RGA.py #
# Created by Sanshiro Enomoto on 18 Aug 2025 


import threading, logging
from slowpy.control import ControlNode, EthernetNode


class RGA(ControlNode):
    def __init__(self, connection):
        self.connection = connection
        self.connection._rga_lock = threading.Lock()
        
        while True:
            line = self.connection.do_get_line(timeout=0.5) or ''
            if len(line) == 0:
                break
            logging.info(f'MKS-RGA: {line}')

        self.notifications = []
        self.has_control = (self.command('Control SlowDash 0.1').get() is not False)
        if self.has_control:
            logging.info("RGA: taking control")

        self.info_node = InfoNode(self)
        self.status_node = StatusNode(self)
        self.scan_node = ScanNode(self)

        
    @classmethod
    def _node_creator_method(cls):
        def mks_rga(self, *args, **kwargs):
            if self.__class__.__name__ != 'EthernetNode':
                raise spc.ControlException('mksrga() can be inserted only to EthernetNode')
            try:
                self.rga_node
            except:
                self.rga_node = RGA(self, *args, **kwargs)

            return self.rga_node

        return mks_rga


    def command(self, *args, **kwargs):
        return CommandNode(self, *args, **kwargs)


    def info(self):
        return self.info_node

    
    def status(self):
        return self.status_node

    
    def scan(self):
        return self.scan_node


    def _communicate(self, command):
        command_name = command.split()[0].lower()
        with self.connection._rga_lock:
            try:
                self.connection.set(command + '\x0d')
            except Exception as err:
                logging.error(f'{err}')
                return None

            while True:
                reply = self._receive_reply(timeout=1)
                if len(reply) == 0:
                    return None
                if reply[0][0].lower() == command_name:
                    break
                self.notifications.append(reply)

        if reply[0][1] != "OK":
            logging.error("error on command: %s" % command)
            for message in reply[1:]:
                logging.error("  %s" % ' '.join(message))
            return False
        
        return reply[1:]

        
    def _receive_reply(self, timeout):
        reply = []
        while True:
            line = self.connection.do_get_line(timeout=timeout)
            if line is None:
                break
            if len(line) == 0:
                if len(reply) == 0:
                    continue
                else:
                    break
            rows = []
            value = ''
            in_quote = False
            is_filled = False
            for ch in line:
                if ch == '"':
                    in_quote = not in_quote
                    is_filled = True
                elif (not in_quote) and (ch in [ ' ', '\t' ]):
                    if is_filled:
                        rows.append(value)
                        value = ''
                        is_filled = False
                else:
                    value = value + ch
                    is_filled = True
            if is_filled:
                rows.append(value)
            if len(rows) > 1:
                reply.append(rows)
            
        return reply

    
    
class CommandNode(ControlNode):
    def __init__(self, rga, command):
        self.rga = rga
        self.command = command

        
    def set(self, value):
        if type(value) is list:
            return self.rga._communicate(f'{self.command} {' '.join(str(v) for v in value)}')
        else:
            return self.rga._communicate(f'{self.command} {value}')

    
    def get(self):
        return self.rga._communicate(self.command)

    
        
class InfoNode(ControlNode):
    def __init__(self, rga):
        self.rga = rga

        
    def get(self):
        record = {}
        for command in [ 'InletInfo', 'FilamentInfo', 'SourceInfo 0', 'MultiplierInfo', 'DetectorInfo 0', 'Info' ]:
            record[command] = {}
            reply = self.rga.command(command).get()
            if reply is None or reply is False:
                record[command]['CommandExecution'] = 'Error'
                continue
            for item in reply:
                record[command][str(item[0])] = ', '.join(item[1:])

        return record



class StatusNode(ControlNode):
    def __init__(self, rga):
        self.rga = rga

        self.scan_settings = {
            'scan_mode': 'Barchart',
            'mass_start': 1,
            'mass_end': 30,
            'filter_mode': 'PeakAverage',  # "PeakCenter", "PeakMax", "PeakAverage"
            'accuracy': 1,                 # 0..8, 0 is the fastest
            'detector_index': 3,   # 0: Faraday, 1..3: Multipliers
        }
            
        
    def get(self):
        record = {
            'System': {
                'Controlling': 'Yes' if self.rga.has_control else 'No',
            },
            'ScanSettings': self.scan_settings,
        }
            
        return record



class ScanNode(ControlNode):
    def __init__(self, rga):
        self.rga = rga

        
    def get(self):
        settings = self.rga.status_node.scan_settings
        cmd = f'Add{settings["scan_mode"]}'
        args = [
            f'SlowdashOneTime',
            f'{settings["mass_start"]} {settings["mass_end"]}',
            f'{settings["filter_mode"]} {settings["accuracy"]} 0 0 {settings["detector_index"]}'
        ]
        
        if not self.rga.has_control:
            return None
        if self.rga.command('ScanStop').get() is False:
            pass

        while len(self.rga.notifications) > 0:
            for record in self.rga.notifications.pop(0):
                logging.warning(f'Leftover notification dropped: {record[0]}')
        
        if self.rga.command(cmd).set(args) is False:
            pass
        if self.rga.command('ScanAdd').set('SlowdashOneTime') is False:
            return None

        
        if self.rga.command('ScanStart').set(1) is False:
            return None

        # BUG: there is a tiny chance that another command is started in between "ScanStart" and "with lock"
        # TODO: implement reply/notification routing
        
        with self.rga.connection._rga_lock:
            table = []
            attr = {}
            while len(table) < int(settings["mass_end"]) - int(settings["mass_start"]):
                reply = self.rga._receive_reply(timeout=1)
                if reply is None:
                    break
                self.rga.notifications.extend(reply)

                k = 0
                while k < len(self.rga.notifications):
                    record = self.rga.notifications[k]
                    record_name = record[0]
                    if record_name == 'MassReading':
                        if record[1] != 'MultSkipped':
                            mass, value = [ float(x) for x in record[1:] ]
                            table.append([mass, value])
                    elif record_name == 'StartingScan':
                        attr['timestamp'] = record[2]
                    elif record_name == 'StartingMeasurement':
                        attr['measurement'] = record[1]
                    elif record_name == 'ZeroReading':
                        attr['zero_reading'] = [ float(x) for x in record[1:] ]
                    else:
                        k += 1
                        continue
                    del self.rga.notifications[k]
            
        if self.rga.command('ScanStop').get() is False:
            pass
        if self.rga.command('MeasurementRemove SlowDashOneTime').get() is False:
            return None
        
        return table, attr


        
#####################
# slowtask-RGA.py #
# Created by Sanshiro Enomoto on 18 Aug 2025 

from slowpy.control import control_system as ctrl


def _initialize(params):
    global rga
    rga = RGA(ctrl.ethernet(host=params.get('address',None), port=10014))
    ctrl.export(rga.info(), 'Info.RGA')
    ctrl.export(rga.status(), 'Status.RGA')
    
    rga.command('CalibrationOptions').set(['Current', 'Current'])


def _run():
    print(rga.info().get())
    print(rga.status().get())
    print(rga.scan().get())



async def run_command(command:str):
    if command.upper() == 'SCANSTART':
        result = 'ERROR: scan cannot be started from command console'
    else:
        result = rga.command(command).get()

    if type(result) is list:
        if len(result) > 0:
            lines = [ f'{row[0]:25s} {", ".join(row[1:])}' for row in result ]
            result = '\n'.join(lines)
        else:
            result = 'OK'
    elif result is False:
        result = f'ERROR: invalid command: {command}'
        
    await ctrl.aio_publish(str(result), name="command_result")

    return True
    

if __name__ =='__main__':
    logging.basicConfig(level=logging.INFO)
    
    from slowpy.dash import Tasklet
    task = Tasklet()
    task.run({
        'address': 'localhost'
    })
