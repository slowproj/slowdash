# control_MKS_RGA.py #
# Created by Sanshiro Enomoto on 18 Aug 2025 


import os, time, socket, threading, logging
from slowpy.control import ControlNode, EthernetNode

app_name = f'SlowDash-{socket.gethostname()}-{os.getpid()}'


class RGA(ControlNode):
    def __init__(self, connection):
        self.connection = connection
        self.connection._rga_lock = threading.Lock()
        
        while True:
            line = self.connection.do_get_line(timeout=0.5) or ''
            if len(line) == 0:
                break
            logging.info(f'MKS-RGA: {line}')

        self.replies = []
        self.notifications = []

        self.info_node = InfoNode(self)
        self.status_node = StatusNode(self)
        self.scan_node = ScanNode(self)

        
    @classmethod
    def _node_creator_method(cls):
        def mks_rga(self, *args, **kwargs):
            if self.__class__.__name__ != 'EthernetNode':
                raise spc.ControlException('mksrga() can be inserted only to an EthernetNode')
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


    def do_acquire_control(self):
        self.command('Control').set(f'{app_name} 0.1')
        self.status_node.has_control = (rga.info().get().get('Info',{}).get('UserApplication',None) == app_name)

        
    def do_release_control(self):
        self.command('Release').set()
        self.status_node.has_control = (rga.info().get().get('Info',{}).get('UserApplication',None) == app_name)

        
    def _communicate(self, command):
        command_name = command.split()[0].lower()
        with self.connection._rga_lock:
            self.replies = []
            try:
                self.connection.set(command + '\x0d')
            except Exception as err:
                logging.error(f'{err}')
                return None

            while True:
                if len(self.replies) > 0:
                    reply = self.replies.pop(0)
                else:
                    reply = self._receive_reply(timeout=10)
                    if reply is None or len(reply) == 0:
                        return None
                if reply[0][0].lower() == command_name:
                    break
                self.notifications.extend(reply)
                logging.warn(f'notification during a command {command}: {reply}')

        if reply[0][1] != "OK":
            logging.error(f'error on command: "{command}"')
            for message in reply[1:]:
                logging.error(f'  {" ".join(message)}')
            return False
        
        return reply[1:]

        
    def _receive_reply(self, timeout):
        reply = []
        while True:
            line = self.connection.do_get_line(timeout=timeout)
            if line is None:
                if len(reply) > 0:
                    break
                else:
                    return None
            if len(line) == 0:
                if len(reply) == 0:
                    time.sleep(timeout/100)
                    continue
                else:
                    break
            row = []
            value = ''
            in_quote = False
            is_filled = False
            for ch in line:
                if ch == '"':
                    in_quote = not in_quote
                    is_filled = True
                elif (not in_quote) and (ch in [ ' ', '\t' ]):
                    if is_filled:
                        row.append(value)
                        value = ''
                        is_filled = False
                else:
                    value = value + ch
                    is_filled = True
            if is_filled:
                row.append(value)
            if len(row) > 1:
                reply.append(row)

        if len(reply) > 0:
            if reply[0][0] == 'FilamentStatus':
                rga.status_node.filament = reply[0][2]
            elif reply[0][0] == 'MultiplierStatus':
                rga.status_node.multiplier = reply[0][1]
            else:
                return reply
            
            return self._receive_reply(timeout)
            
        return reply

    
    
class CommandNode(ControlNode):
    def __init__(self, rga, command):
        self.rga = rga
        self.command = command

        
    def set(self, value=None):
        if value is None:
            return self.rga._communicate(self.command)
        elif type(value) is list:
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
        for command in [ 'FilamentInfo', 'SourceInfo 0', 'MultiplierInfo', 'DetectorInfo 0', 'Info' ]:
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

        self.scan_mode = 'Barchart'       # 'Barchart' or 'Analog'
        self.mass_start = 1
        self.mass_end = 100               # up to 200 (see the Info command output)
        self.filter_mode = 'PeakAverage'  # "PeakCenter", "PeakMax", "PeakAverage"
        self.points_per_peak = 8          # (64), 32, 16, 8, 4
        self.accuracy = 3                 # 0..8, 0 is the fastest
        self.detector_index = 3           # 0: Faraday, 1..3: Multipliers

        # status set by the controller (ScanNode etc)
        self.has_control = False
        self.filament = 'OFF'
        self.multiplier = 'Off'
        self.scanning = False
        self.last_mass = 0

        
    def get(self):
        return {
            'Settings': {
                'scan_mode': self.scan_mode,
                'mass_start': self.mass_start,
                'mass_end': self.mass_end,
                'filter_mode': self.filter_mode,
                'points_per_peak': self.points_per_peak,
                'accuracy': self.accuracy,
                'detector_index': self.detector_index,
            },
            'Status': {
                'has_control': self.has_control,
                'filament': self.filament,
                'multiplier': self.multiplier,
                'scanning': self.scanning,
                'last_mass': self.last_mass,
            }
        }



class ScanNode(ControlNode):
    def __init__(self, rga):
        self.rga = rga

        
    def get(self):
        if not self.rga.status_node.has_control:
            return None
        
        if self.rga.status_node.scanning:
            return None
        
        settings = self.rga.status_node
        scan_mode = ('Analog' if settings.scan_mode == 'Analog' else 'Barchart')
        cmd = f'Add{scan_mode}'
        args = [
            'SlowdashOneTime',   # Measurement Name
            settings.mass_start, settings.mass_end,
            settings.filter_mode if scan_mode == "Barchart" else settings.points_per_peak,
            settings.accuracy,
            '0',   # EGainIndex
            '0',   # SourceInde
            settings.detector_index,
        ]
        
        if self.rga.command('ScanStop').set() is False:
            pass
        with self.rga.connection._rga_lock:
            while len(self.rga.notifications) > 0:
                for record in self.rga.notifications.pop(0):
                    logging.warning(f'Leftover notification dropped: {record}')
        
        if self.rga.command(cmd).set(args) is False:
            pass
        if self.rga.command('ScanAdd').set('SlowdashOneTime') is False:
            return None
        if self.rga.command('ScanStart').set(1) is False:
            return None
        self.rga.status_node.scanning = True
        self.rga.status_node.last_mass = 0
        
        table = []
        attr = {}
        length = int(settings.mass_end) - int(settings.mass_start) + 1
        if scan_mode == "Analog":
            length *= settings.points_per_peak
        while len(table) < length:
            if len(self.rga.notifications) == 0:
                reply = self.rga._receive_reply(timeout=10)
                if reply is None:
                    break
                self.rga.notifications.extend(reply)

            with self.rga.connection._rga_lock:
                for record in self.rga.notifications:
                    record_name = record[0]
                    if record_name == 'MassReading':
                        if record[1] != 'MultSkipped':
                            mass, value = [ float(x) for x in record[1:] ]
                            table.append([mass, value])
                            self.rga.status_node.last_mass = mass
                    elif record_name == 'StartingScan':
                        attr['timestamp'] = record[2]
                    elif record_name == 'StartingMeasurement':
                        attr['measurement'] = record[1]
                    elif record_name == 'ZeroReading':
                        attr['zero_reading'] = [ float(x) for x in record[1:] ]
                    else:
                        self.rga.replies.append(record)
                self.rga.notifications = []
            
        self.rga.status_node.scanning = False
        self.rga.status_node.last_mass = 0
        
        if self.rga.command('ScanStop').set() is False:
            pass
        if self.rga.command('MeasurementRemove').set('SlowDashOneTime') is False:
            pass
        
        return table, attr


        
#####################
# slowtask-RGA.py #
# Created by Sanshiro Enomoto on 18 Aug 2025 

import time, datetime, math, json
import slowpy
from slowpy.control import control_system as ctrl
from dataclasses import dataclass


@dataclass
class RunControl:
    running: bool = False
    scan_interval: float = 60
    next_scan_time: float = 0
    time_to_next_scan: float = 0
    ready_to_start: bool = False
run_control = RunControl()


async def _initialize(params):
    global rga, datastore_ts, datastore_obj
    
    address = params.get('address', 'localhost')
    rga = RGA(ctrl.ethernet(address, port=10014))
    
    db_url = params.get('db_url', 'sqlite:///RGA.db')
    datastore_ts = slowpy.store.create_datastore_from_url(db_url, table='numeric_data')
    datastore_obj = slowpy.store.create_datastore_from_url(db_url, table='json_data')
    
    ctrl.export(rga.status(), name='Status.RGA')
    await ctrl.aio_publish(run_control, name="RunControl.RGA")
    await ctrl.aio_publish(rga.info(), name='Info.RGA')


async def _finalize():
    global datastore_ts, datastore_obj
    if datastore_ts:
        datastore_ts.close()
    if datastore_obj:
        datastore_obj.close()
    

async def _loop():
    if not rga.status_node.scanning: # other command thread might be running a scan
        # update the status from the info command (not from notifications) in case of socket reconnect
        info = rga.info().get()
        rga.status_node.has_control = (info.get('Info',{}).get('UserApplication',None) == app_name)
        rga.status_node.filament = (info.get('FilamentInfo',{}).get('SummaryState','Error'))
        run_control.ready_to_start = (
            rga.status_node.has_control
            and (rga.status_node.filament == 'ON')
            and (not run_control.running)
        )
        await ctrl.aio_publish(run_control)
        await ctrl.aio_publish(rga.status())
        
    if not rga.status_node.has_control:
        run_control.running = False
    if not run_control.running:
        run_control.time_to_next_scan = 0
        return await ctrl.aio_sleep(1)
    
    now = time.time()
    if run_control.next_scan_time == 0:
        run_control.next_scan_time = now
        
    if run_control.scan_interval > 0:
        run_control.time_to_next_scan = run_control.next_scan_time - now
    else:
        run_control.time_to_next_scan = 0
    if now < run_control.next_scan_time:
        return await ctrl.aio_sleep(min(1, run_control.next_scan_time-now))
    
    run_control.time_to_next_scan = 0
    await ctrl.aio_publish(run_control)
    
    result = rga.scan().get()
    
    if run_control.scan_interval > 0:
        ticks = math.floor((now - run_control.next_scan_time) / run_control.scan_interval) + 1
        run_control.next_scan_time += ticks * run_control.scan_interval
        run_control.time_to_next_scan = run_control.next_scan_time - now
    else:
        run_control.next_scan_time = 0
        run_control.running = False
            
    if result is None:
        return
    table, attr = result
    
    g0 = slowpy.Graph()
    g1 = slowpy.Graph()
    cumulative = 0
    g1.add_point(0, cumulative)
    for row in table:
        mbar = row[1]/100.0
        cumulative += mbar
        g0.add_point(row[0], mbar)
        g1.add_point(row[0], cumulative)
    timestamp = float(attr.get('_timestamp', time.time()))
    if timestamp > 0:
        tz = datetime.datetime.now().astimezone().tzinfo
        g0.add_stat('Date', datetime.datetime.fromtimestamp(timestamp,tz=tz).strftime('%Y-%m-%d (%z)'))
        g0.add_stat('Time', datetime.datetime.fromtimestamp(timestamp,tz=tz).strftime('%H:%M:%S'))
        g1.add_stat('Sum', f'{cumulative:.3g} mbar')
    datastore_obj.append(g0, tag="graph.MassSpec.RGA")
    datastore_obj.append(g1, tag="graph_cumulative.MassSpec.RGA")
    await ctrl.aio_publish(g0, name="graph.MassSpec.RGA")
    await ctrl.aio_publish(g1, name="graph_cumulative.MassSpec.RGA")

    if rga.status().scan_mode == 'Barchart':
        datastore_ts.append({ f'mbar.Mass{row[0]:02.0f}.RGA':row[1]/100 for row in table })
        datastore_ts.append({f'mbar.Sum.RGA':cumulative})
    
    datastore_obj.append({'Status.RGA': json.dumps({'tree':rga.status().get()})})
    datastore_obj.append({'Info.RGA': json.dumps({'tree':rga.info().get()})})

    
async def acquire_control():
    rga.do_acquire_control()
    if not rga.status_node.has_control:
        logging.warn("RGA: unable to take control")
    else:
        logging.info("RGA: taking control")
            
    return True

            
async def release_control():
    rga.do_release_control()
    if rga.status_node.has_control:
        logging.warn("RGA: unable to release control")
    else:
        logging.info("RGA: release control")
            
    return True

                
async def filament_on():
    if rga.command('FilamentControl').set('On') is False:
        pass
    return True

            
async def filament_off():
    if rga.command('FilamentControl').set('Off') is False:
        pass
    return True


async def start(scan_mode:str, filter_mode:str, points_per_peak:int, mass_start:int, mass_end:int, accuracy:int, detector:int, interval:float):    
    rga.status_node.scan_mode = ('Analog' if scan_mode == 'Analog' else 'Barchart')
    rga.status_node.mass_start = max(0, min(mass_start, mass_end))
    rga.status_node.mass_end = min(max(mass_start, mass_end), 200)
    rga.status_node.filter_mode = filter_mode
    rga.status_node.points_per_peak = max(4, min(64, points_per_peak))
    rga.status_node.accuracy = accuracy
    rga.status_node.detector_index = detector

    run_control.scan_interval = max(0, interval)
    run_control.next_scan_time = time.time()
    run_control.running = True
    await ctrl.aio_publish(run_control)

    
async def stop(scan_mode:str, filter_mode:str, points_per_peak:int, mass_start:int, mass_end:int, accuracy:int, detector:int, interval:float):
    rga.status_node.scan_mode = ('Analog' if scan_mode == 'Analog' else 'Barchart')
    rga.status_node.mass_start = max(0, min(mass_start, mass_end))
    rga.status_node.mass_end = min(max(mass_start, mass_end), 200)
    rga.status_node.filter_mode = filter_mode
    rga.status_node.points_per_peak = max(4, min(64, points_per_peak))
    rga.status_node.accuracy = accuracy
    rga.status_node.detector_index = detector

    run_control.scan_interval = max(0, interval)
    run_control.running = False
    await ctrl.aio_publish(run_control)

    
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
    
    run_control.running = True
    
    from slowpy.dash import Tasklet
    task = Tasklet()
    task.run({
        'address': 'localhost',
        'db_url': 'sqlite:///RGA.db'
    })
