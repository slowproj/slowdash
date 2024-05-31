import sys, time

import dripline
ifc = dripline.core.Interface(dripline_config={'auth-file':'/project/authentications.json'})

target, ramp, is_ramping = None, None, False


def _get_channels():
    return [ {'name': 'peaches_status', 'type': 'tree'} ]


def _get_data(channel):
    if channel == 'peaches_status':
        return { 'tree': { 'ramping': is_ramping } }
    return None


def _loop():
    global target, ramp, is_ramping
    try:
        current = ifc.get('peaches').payload.to_python().get('value_raw', None)
        next_value = None
        if current is not None:
            diff = abs(target - current)
            if diff < 1e-5 * (abs(target)+abs(current)+1e-10):
                pass
            elif ramp is None or ramp < 1e-10 or diff < ramp:
                next_value = target
            elif target > current:
                next_value = current + ramp
            else:
                next_value = current - ramp
        if next_value is not None:
            is_ramping = True
            ifc.set('peaches', next_value)
        else:
            is_ramping = False
    except Exception as e:
        pass
        
    time.sleep(1)

    
def _process_command(doc):
    global target, ramp
    try:
        if doc.get('set', False):
            if doc.get('target', None):
                target = float(doc.get('target', target))
            if doc.get('ramp', None):
                ramp = abs(float(doc.get('ramp', ramp)))
        else:
            return False
    except Exception as e:
        return { "status": "error", "message": str(e) }

    return True



if __name__ == '__main__':
    target = 10
    ramp = 0.1
    while True:
        _loop()
