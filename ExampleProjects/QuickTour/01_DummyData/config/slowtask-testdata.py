
import slowpy
device = slowpy.control.RandomWalkDevice()
datastore = slowpy.store.DataStore_SQLite('sqlite:///SlowStore.db', table='slowdata')
tasklet = slowpy.mesh.Tasklet()


@tasklet.loop(interval=1.0)
def loop():
    for ch in range(4):
        data = device.read(ch)
        datastore.append(data, tag=f'ch{ch:02d}')
    
    
if __name__ == '__main__':
    tasklet.run()
