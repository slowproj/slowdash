
import dripline
ifc = dripline.core.Interface()

def set_peaches(value:float):
    print(f'setting peaches to {value}')
    ifc.set('peaches', value)
