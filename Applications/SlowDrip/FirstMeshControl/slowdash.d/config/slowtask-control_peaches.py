
import dripline
ifc = dripline.core.Interface()

print('hello from control_peaches.py')


def set_peaches(value:float):
    print(f'setting peaches to {value}')
    ifc.set('peaches', value)
    return True
