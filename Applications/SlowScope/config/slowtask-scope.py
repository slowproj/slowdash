import time

from slowpy.control import ControlSystem, ControlNode
ctrl = ControlSystem()
ctrl.import_control_module('VISA')
scope = None

config = {
    'trigger_source': 'channel1',
    'trigger_edge': 'positive',
    'trigger_level': 0.1,
    'timebase_range': 0.01,
    'ch1_range': 4.0,
    'ch2_range': 4.0,
    'readout_interval': 2.0,
    'store_interval': 10.0,
    'running': False,
    'next_readout': 0,
}

class ConfigNode(ControlNode):
    def get(self):
        return { 'tree': config }

def _export():
    return [ ('config', ConfigNode()) ]



from slowpy import Graph
from slowpy.store import DataStore_Redis
datastore = DataStore_Redis('redis://localhost/1')


def _initialize(params):
    global scope
    visa_addr = params.get('visa', None)
    if visa_addr is None:
        return
    scope = ctrl.visa(visa_addr).scpi(append_opc=True)
    print(scope.command('*idn?').get())
    scope.command('*RST').set()
    
    scope.command(':channel1:probe').set(1)
    scope.command(':channel2:probe').set(1)
    scope.command(':channel1:offset').set(0)
    scope.command(':channel2:offset').set(0)
    scope.command(':timebase:mode').set('main')
    scope.command(':timebase:reference').set('center')
    scope.command(':timebase:delay').set(0)
    scope.command(':trigger:source').set('channel1') # channel1, channel2, or external
    scope.command(':trigger:sweep').set('normal')  # normal or auto
    scope.command(':acquire:type').set('normal')   # normal or average
    scope.command(':waveform:points').set(1000)    # 100, 250, 500, or 1000
    scope.command(':waveform:format').set('ascii')

    config_scope()
    config['running'] = False


def _loop():
    next_readout = config['next_readout']
    now = time.time()
    if now < next_readout:
        time.sleep(0.1)
        return
    
    if scope is not None and config['running']:
        acquire()
        
    while now > next_readout:
        next_readout += config['readout_interval']
    config['next_readout'] = next_readout
    

def config_scope(**kwargs):
    def update(item, valid=float):
        value = kwargs.get(item, None)
        if value is None:
            return
        if type(valid) is list:
            if value not in valid:
                return
        else:
            try:
                value = valid(value)
            except:
                return
        config[item] = value
        
    update('trigger_source', ['channel1', 'channel2', 'external'])
    update('trigger_level', float)
    update('trigger_edge', ['positive', 'negative'])
    update('timebase_range', float)
    update('ch1_range', float)
    update('ch2_range', float)
    
    scope.command(':channel1:range').set(config['ch1_range'])
    scope.command(':channel2:range').set(config['ch2_range'])
    scope.command(':timebase:range').set(config['timebase_range'])
    scope.command(':trigger:source').set(config['trigger_source'])
    scope.command(':trigger:slope').set(config['trigger_edge'])
    scope.command(':trigger:level').set(config['trigger_level'])
    
    return True



def start(**kwargs):
    if scope is not None:
        config['running'] = True
    return True



def stop(**kwargs):
    config['running'] = False
    return True



def single(**kwargs):
    acquire()
    return True



def acquire():
    if scope is None:
        return
    
    scope.command(':digitize').set('channel1,channel2')
    data1 = scope.command(':waveform:source channel1; data?').get()
    data2 = scope.command(':waveform:source channel2; data?').get()
    t_max = float(scope.command(':timebase:range?').get())
    data1 = data1[int(data1[1])+2:] # remove the header
    data2 = data2[int(data2[1])+2:] # remove the header
    x1 = [ float(xk.strip()) for xk in data1.split(r',') ]
    x2 = [ float(xk.strip()) for xk in data2.split(r',') ]
    t = [ t_max * float(k)/len(x1) for k in range(len(x1)) ]

    g_x1, g_x2, g_xy = Graph(), Graph(), Graph()
    g_x1.add_point(t, x1)
    g_x2.add_point(t, x2)
    g_xy.add_point(x1, x2)

    datastore.update(g_x1, tag='ch1')
    datastore.update(g_x2, tag='ch2')
    datastore.update(g_xy, tag='xy')

    
            
if __name__ == '__main__':
    _initialize({'visa': 'TCPIP-HISLIP::192.168.42.6::INSTR'})
    acquire()
