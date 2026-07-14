
from slowpy.mesh import Tasklet, DataPacket
tasklet = Tasklet()


#### Data Store Service (Subscribe and Store) ####

from slowpy.store import DataStore_SQLite
datastore = DataStore_SQLite('sqlite:///TestData.db', table='slowdata')


@tasklet.mesh.on('data.store.>')
def store(data:DataPacket):
    print(f'STORE DATA: {data.values}')
    datastore.append(data.values)

    
#### Control Node Export  ####
    
import shutil
from slowpy.control import ControlNode

class DiskUsageNode(ControlNode):
    async def aio_get(self):
        total, used, free = tuple((int(x*1e-8)/10.0) for x in shutil.disk_usage('.'))
        return {
            'tree': {
                'total_GB': total,
                'used_GB': used,
                'free_GB': free,
                'used_percent': int(100 * used/total) if total > 0 else 100
            }
        }

tasklet.mesh.export('disk_usage', DiskUsageNode())



#### Config Content Generation (HTML) ####

import datetime

@tasklet.content('config/html-disk_usage.html')
def html_disk_usage():
    total, used, free = tuple((int(x*1e-8)/10.0) for x in shutil.disk_usage('.'))
    used_percent = int(100 * used/total) if total > 0 else 100
    return f'''
        <span style="font-size:300%">{used_percent}</span>
        <span style="font-size:250%">% used</span>
        <p>
        <table>
          <tr><td>Total</td><td>{total} GB</td></tr>
          <tr><td>Used</td><td>{used} GB</td></tr>
          <tr><td>Free</td><td>{free} GB</td></tr>
        </table>
        <p>
        As of {str(datetime.datetime.now())}
    '''



#### Standalone Execution  ####
    
if __name__ == '__main__':
    tasklet.run(slowdash_url='http://localhost:18881')
