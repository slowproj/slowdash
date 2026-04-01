
from slowpy.control import control_system as ctrl
http = ctrl.http('http://localhost:18881')
slowdash = http.import_control_module('Slowdash').slowdash()


print("ping -> ", slowdash.ping())
print("config -> ", slowdash.config())
print("channels -> ", slowdash.channels())


print(slowdash.config_file('slowplot-trash.json').set('{"message": "hello"}'))
print(slowdash.config_file('slowplot-trash.json'))


ctrl.stop_by_signal()
while not ctrl.is_stop_requested():
    try:
        print("data/ch0,ch1 -> ", slowdash.data('ch0,ch1',length=60))
    except Exception:
        pass
    
    ctrl.sleep(1)
