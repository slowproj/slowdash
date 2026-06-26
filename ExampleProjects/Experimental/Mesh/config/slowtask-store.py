

from slowpy.mesh import Tasklet
tasklet = Tasklet()


from slowpy.store import DataStore_SQLite
datastore = DataStore_SQLite('sqlite:///TestData.db', table='slowdata')


@tasklet.mesh.on('data.store.>')
def store(data_record):
    print(f'STORE: {data_record}')
    datastore.append(data_record)


    
if __name__ == '__main__':
    tasklet.run(slowdash_url='http://localhost:18881')
