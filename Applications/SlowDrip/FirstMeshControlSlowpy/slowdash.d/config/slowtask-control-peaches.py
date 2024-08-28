
from slowpy.control import ControlSystem, ControlNode
ctrl = ControlSystem()

ctrl.import_control_module('Dripline')
dripline = ctrl.dripline(dripline_config={'auth-file':'/authentications.json'})

peaches = dripline.endpoint("peaches")


def set_peaches(target, ramping, **kwargs):
    print(f'setting peaches to {target}, with ramping at {ramping}')
    peaches.ramping(ramping).set(target)

    
class StatusNode(ControlNode):
    def get(self):
        return {
            'target': peaches.ramping().get(),
            'ramping': peaches.ramping().status().get()
        }

    
def _export():
    return [
        ('peaches', peaches),
        ('status', StatusNode())
    ]
