
from slowpy.control import ControlSystem
dripline = ControlSystem.import_control_module('Dripline').dripline(
    dripline_config={'auth-file':'/root/authentications.json'}
)

peaches = dripline.endpoint("peaches")


class StatusNode(slowpy.ControlNode):
    def get(self):
        return {
            'ramping': peaches.ramp().status().get()
        }
    
def _export():
    return [
        ('peaches', peaches),
        ('status', StatusNode())
    ]

def set(target, ramping, **kwargs):
    print("setting peaches to " + target + ", with ramping=" + ramping)
    peaches.ramp(ramping).set(target)
