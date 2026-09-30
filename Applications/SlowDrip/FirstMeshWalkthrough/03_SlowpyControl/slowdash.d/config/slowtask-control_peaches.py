
import slowpy
tasklet = slowpy.mesh.Tasklet()

from slowpy.control import control_system as ctrl
ctrl.import_control_module('Dripline')

rmq_url = tasklet.parameters.get('RMQ_URL', 'amqp://dripline:dripline@localhost')
dripline = ctrl.dripline(rmq_url)
peaches = dripline.endpoint('peaches').value_raw()
chips = dripline.endpoint('chips')
print('hello from peaches')

#ctrl.bind_tasklet(tasklet)
#ctrl.export(peaches.ramping(), name='ramping_target')
#ctrl.export(peaches.ramping().status(), name='ramping_status')


@tasklet.mesh.export()
def set_peaches(target:float, ramping_rate:float):
    print(f'setting peaches to {target}, with ramping at {ramping_rate}')
    #print(f'current chips: {chips.get()}')
    #print(f'current peaches: {peaches.get()}')
    #peaches.ramping(ramping_rate).set(target)
    peaches.set(target)

    
@tasklet.mesh.export()
def abort_ramping():
#    peaches.ramping().set(None)
    print(f'current chips: {chips.get()}')
    print(f'current peaches: {peaches.get()}')
