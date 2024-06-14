#! /bin/env python3


from slowpy.control import ControlSystem
ctrl = ControlSystem()


host, port = '192.168.1.43', 17674

device_id = ctrl.ethernet(host, port).scpi('*IDN')
V0 = ctrl.ethernet(host, port).scpi('MEAS:V0', set_format='V0 {};*OPC?')


if __name__ == '__main__':
    print('ID: %s' % str(device_id))
    
    ctrl.stop_by_signal()
    while not ctrl.is_stop_requested():
        V0.ramp(1).set(10)
        for i in range(10):
            print(V0)
            if not ctrl.sleep(1):
                break
