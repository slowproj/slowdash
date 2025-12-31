
from slowpy.control import control_system as ctrl
ctrl.import_control_module('Dripline')

dripline = ctrl.dripline('amqp://dripline:dripline@rabbit-broker')
print(f'hello from {__name__}')


import random

def _loop():
    step = abs(random.gauss(0, 10))
    print(f"Script: setting the step to {step}")
    dripline.endpoint('randomwalk_step').set(step)
    ctrl.sleep(10)



# make this script independently executable
if __name__ == '__main__':
    from slowpy.dash import Tasklet
    Tasklet().run()
