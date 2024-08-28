
import dripline
ifc = dripline.core.Interface(dripline_config={'auth-file':'/authentications.json'})

def set_peaches(value, **kwargs):
    print(f'setting peaches to {value}')
    ifc.set('peaches', value)
