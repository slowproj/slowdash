#! /bin/env python3


from slowpy.control import ControlSystem
ctrl = ControlSystem()


host, port = '192.168.1.29', 17674

device_id = ctrl.ethernet(host, port).scpi().command('*IDN')
V0 = ctrl.ethernet(host, port).scpi().command('MEAS:V0', set_format='V0 {};*OPC?')


if __name__ == '__main__':
    ctrl.ethernet(host, port).do_flush_input()
    print('ID: %s' % str(device_id))
    
    V0.setpoint().set(10)
    
    ctrl.stop_by_signal()
    while not ctrl.is_stop_requested():
        
        print(f'ramping to {-float(V0.setpoint())}...')
        V0.ramping(1).set(-float(V0.setpoint()))
        
        for i in range(10):
            print(V0)
            if not ctrl.sleep(1):
                break
