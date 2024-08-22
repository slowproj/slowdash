import sys, time

import dripline
ifc = dripline.core.Interface(dripline_config={'auth-file':'/project/authentications.json'})

target, ramping, is_ramping = None, None, False


def _get_channels():
    return [ {'name': 'peaches_status', 'type': 'tree'} ]


def _get_data(channel):
    if channel == 'peaches_status':
        return { 'tree': { 'ramping': is_ramping } }
    return None


def _loop():
    global target, ramping, is_ramping
    try:
        current = ifc.get('peaches').payload.to_python().get('value_raw', None)
        next_value = None
        if current is not None:
            diff = abs(target - current)
            if diff < 1e-5 * (abs(target)+abs(current)+1e-10):
                pass
            elif ramping is None or ramping < 1e-10 or diff < ramping:
                next_value = target
            elif target > current:
                next_value = current + ramping
            else:
                next_value = current - ramping
        if next_value is not None:
            is_ramping = True
            ifc.set('peaches', next_value)
        else:
            is_ramping = False
    except Exception as e:
        pass
        
    time.sleep(1)

    
def _process_command(doc):
    global target, ramping
    try:
        if doc.get('set', False):
            if doc.get('target', None):
                target = float(doc.get('target', target))
            if doc.get('ramping', None):
                ramping = abs(float(doc.get('ramping', ramping)))
            print(f'setting peaches to {target}, with ramping={ramping}')
        else:
            return False
    except Exception as e:
        return { "status": "error", "message": str(e) }

    return True



if __name__ == '__main__':
    target = 10
    ramping = 0.1
    while True:
        _loop()
