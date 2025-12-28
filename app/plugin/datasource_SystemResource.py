# Created by Sanshiro Enomoto on 2 November 2022 #

# pip3 install psutil


import sys, os, time, subprocess, socket, logging, datetime
from sd_datasource import DataSource

try:
    import psutil
except:
    pass
        


class DataSource_SystemResource(DataSource):
    def __init__(self, app, project, params):
        super().__init__(app, project, params)
        self.disk_path = params.get('disk_path', project.project_dir)

        
    def get_channels(self):
        return [ { 'name': 'system', 'type': 'tree' } ]

    
    def get_timeseries(self, channels, length, to, resampling=None, reducer='last', envelope=0):
        return {}

    
    def get_object(self, channels, length, to):
        result = {}

        for ch in channels:
            if ch != 'system':
                continue

            now = time.time()
            if now < to - length or now > to + 5:
                continue

            ip = self.get_ip()
            cpu = self.get_cpu_usage()
            mem = self.get_memory_usage()
            disk = self.get_disk_usage()
            battery = self.get_battery_status()
            
            result[ch] = {
                'start': to-length, 'length': length,
                't': now - (to - length),
                'x': {
                    'tree': {
                        'CPU': {
                            'Percent': cpu.get('percent', 'N/A'),
                            'Temperature': cpu.get('temperature', 'N/A')
                        },
                        'Memory': {
                            'Size_GB': mem.get('total', 'N/A'),
                            'Free_GB': mem.get('available', 'N/A')
                        },
                        'Disk': {
                            'Size_GB': disk.get('total', 'N/A'),
                            'Free_GB': disk.get('free', 'N/A')
                        },
                        'Network': {
                            'Address': ip
                        },
                        'Battery': {
                            'Percent': battery.get('percent', 'N/A'),
                            'Hour': battery.get('hoursleft', 'N/A')
                        }
                    }
                }
            }
            
        return result

    
    def get_ip(self, index=0):
        ip_list = []
        try:
            net = psutil.net_if_addrs()
        except:
            return 'N/A'
        for nic_name, nic in net.items():
            for addr in nic:
                if addr.family != socket.AF_INET:
                    continue
                if addr.broadcast is None: # localhost
                    continue
                ip_list.append(addr.address)
                
        if len(ip_list) > index:
            return ip_list[index]
        else:
            return 'N/A'
                

    
    def get_cpu_usage(self):
        record = {}
        try:
            record['percent'] = psutil.cpu_percent()
        except :
            record['percent'] = 'N/A'
        try:
            temps = [ temp.current for temp in psutil.sensors_temperatures()['coretemp'] ]
            record['temperature'] = max(temps)
        except:
            record['temperature'] = 'N/A'
        return record

    
    def get_memory_usage(self):
        try:
            usage = psutil.virtual_memory()
            return {
                'total': int(usage.total * 1e-8)/10.0,  # in GB
                'used': int(usage.used * 1e-8)/10.0,  # in GB
                'available': int(usage.available * 1e-8)/10.0, # in GB
                'percent': usage.percent
            }
        except :
            return {
                'total': 'NA',
                'used': 'NA',
                'available': 'NA',
                'percent': 'NA'
            }

        
    def get_disk_usage(self):
        try:
            usage = psutil.disk_usage(self.disk_path)
            return {
                'total': int(usage.total * 1e-8)/10.0,  # in GB
                'used': int(usage.used * 1e-8)/10.0,  # in GB
                'free': int(usage.free * 1e-8)/10.0,  # in GB
                'percent': usage.percent
            }
        except :
            return {
                'total': 'N/A',
                'used': 'N/A',
                'free': 'N/A',
                'percent': 'N/A'
            }

        
    def get_battery_status(self):
        try:
            status = psutil.sensors_battery()
            return {
                'percent': int(10*status.percent)/10,
                'hoursleft': int(status.secsleft / 360)/10.0
            }
        except :
            return {
                'percent': 'N/A',
                'hoursleft': 'N/A'
            }
        
