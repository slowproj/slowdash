from slowpy.mesh import Tasklet
tasklet = Tasklet()

from slowpy.control import control_system as ctrl
device = ctrl.import_control_module('DummyDevice').randomwalk_device()
ch0, ch1, ch2, ch3 = [ device.ch(ch) for ch in range(4) ]
print("Random-Walk Device Loaded")

import slowpy.store
datastore = slowpy.store.create_datastore_from_url('sqlite:///SlowTaskTest.db', 'test')


@tasklet.mesh.export()
def set(ch:int, V0:float, V1:float, V2:float, V3:float, ramping:float):
    if ch == 0:
        ch0.ramping(ramping).set(V0)
    elif ch == 1:
        ch1.ramping(ramping).set(V1)
    elif ch == 2:
        ch2.ramping(ramping).set(V2)
    elif ch == 3:
        ch3.ramping(ramping).set(V3)

        
@tasklet.mesh.export()
def stop():
    ch0.ramping().set(None)
    ch1.ramping().set(None)
    ch2.ramping().set(None)
    ch3.ramping().set(None)


@tasklet.loop(interval=1.0)
def loop():
    for ch in range(4):
        x = float(device.ch(ch).get())
        datastore.append(x, tag='ch%02d'%ch)

    # send out the ramping status as tree data
    status = {
        'columns': [ 'Channel', 'Current Value', 'Target Value', 'Ramping' ],
        'table': [
            [
                f'Ch{i}',
                ch.get(),
                target if (target := ch.ramping().get()) is not None else '-',
                'Yes' if ch.ramping().status().get() else 'No'
            ]
            for i, ch in enumerate([ch0, ch1, ch2, ch3])
        ]
    }
    ctrl.stream('ramping.status', status)

    
@tasklet.content('config/html-test.html')
def html():
    return '''
        <form name="test">
        Ramping: <input type="number" name="ramping" value="1" style="width:5em">/sec
        <p>
        V0: <input type="number" name="V0" step="any" value="0"><button name="test.set(ch=0)">Set</button><br>
        V1: <input type="number" name="V1" step="any" value="0"><button name="test.set(ch=1)">Set</button><br>
        V2: <input type="number" name="V2" step="any" value="0"><button name="test.set(ch=2)">Set</button><br>
        V3: <input type="number" name="V3" step="any" value="0"><button name="test.set(ch=3)">Set</button><br>
        <p>
        <button name="test.stop()">Stop Ramping</button>
        </form>
    '''
    
    
if __name__ == '__main__':
    tasklet.run()
