
from slowpy.control import ControlSystem, ControlNode
ctrl = ControlSystem()
ctrl.import_control_module('Dripline')
dripline = ctrl.dripline(dripline_config={'auth-file':'/home/slowuser/authentications.json'})

peaches = dripline.endpoint("peaches")


class StatusNode(ControlNode):
    def get(self):
        return {
            'ramping': peaches.ramping().status().get()
        }
    
def _export():
    return [
        ('peaches', peaches),
        ('status', StatusNode())
    ]

def set(target, ramping, **kwargs):
    print("setting peaches to " + target + ", with ramping=" + ramping)
    peaches.ramping(ramping).set(target)
