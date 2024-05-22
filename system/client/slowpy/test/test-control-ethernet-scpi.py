#! /bin/env python3


import time
host, port = '10.19.72.198', 17674
#host, port = '192.168.1.43', 17674


import slowpy as slp
ctrl = slp.ControlSystem()


ep_id = ctrl.ethernet(host, port).scpi('*idn')
print("ID: %s" % str(ep_id))

V0 = ctrl.ethernet(host, port).scpi('MEAS:V0')
for i in range(10):
    print(float(V0)*2.3)
    time.sleep(1)

V0.set(-10)

for i in range(10):
    print(float(V0)*2.3)
    time.sleep(1)
