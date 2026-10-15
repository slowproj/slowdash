import slowpy
tasklet = slowpy.mesh.Tasklet()

datastore = slowpy.store.DataStore_SQLite('sqlite:///SlowStore.db', table="slowdata")

@tasklet.mesh.on('data.store.>')
async def store(data: slowpy.mesh.DataPacket):
    datastore.append(data.values)
