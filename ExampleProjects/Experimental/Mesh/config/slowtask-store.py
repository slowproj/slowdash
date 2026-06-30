

from slowpy.mesh import Tasklet
tasklet = Tasklet()


#### Data Store Service (Subscribe and Store) ####

from slowpy.store import DataStore_SQLite
datastore = DataStore_SQLite('sqlite:///TestData.db', table='slowdata')


@tasklet.mesh.on('data.store.>')
def store(data_record):
    print(f'STORE: {data_record}')
    datastore.append(data_record)

    
#### Control Node Export  ####
    
import shutil
from slowpy.control import ControlNode

class DiskUsageNode(ControlNode):
    async def aio_get(self):
        total, used, free = ((int(float(x)*1e-8)/10) for x in shutil.disk_usage('.'))
        return {
            'tree': {
                'total_GB': total,
                'used_GB': used,
                'free_GB': free,
                'used_percent': int(100 * used/total) if total > 0 else 100
            }
        }

tasklet.mesh.export('disk_usage', DiskUsageNode())


#### Standalone Execution  ####
    
if __name__ == '__main__':
    tasklet.run(slowdash_url='http://localhost:18881')
