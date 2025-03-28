
import dripline
ifc = dripline.core.Interface(username="dripline", password='dripline')

def set_peaches(value, **kwargs):
    print(f'setting peaches to {value}')
    ifc.set('peaches', value)
