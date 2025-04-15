
import dripline
ifc = dripline.core.Interface(username="dripline", password='dripline', dripline_mesh={'broker': 'rabbit-broker'})

def set_peaches(value:float):
    print(f'setting peaches to {value}')
    ifc.set('peaches', value)
