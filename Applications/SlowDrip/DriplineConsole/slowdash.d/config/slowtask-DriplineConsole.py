
import time, datetime, re, json, collections, asyncio
from slowpy.control import ControlNode, control_system as ctrl
ctrl.import_control_module('AsyncDripline')

dripline = None
sensor_values = {}
heartbeats = {}
status_messages = collections.deque(maxlen=10)
replies = collections.deque(maxlen=10)


def timestr(timestamp, now):
    if type(timestamp) in [int, float]:
        unix_time = timestamp
    elif type(timestamp) is str:
        unix_time = datetime.datetime.fromisoformat(timestamp.replace('Z','+00:00')).timestamp()
    else:
        return '---'

    # inside a docker container, the system timezone is UTC, so the display time will be in UTC
    lapse = now-unix_time
    if lapse < 3600:
        date = datetime.datetime.fromtimestamp(unix_time).strftime('%H:%M:%S')
        t = date + f"  ({lapse:.0f} sec ago)"
    elif lapse < 86400:
        date = datetime.datetime.fromtimestamp(unix_time).strftime('%a, %H:%M')
        t = date + f"  ({lapse/3600.0:.1f} hours ago)"
    else:
        date = datetime.datetime.fromtimestamp(unix_time).strftime('%b %d, %H:%M')
        t = date + f"  ({lapse/86400.0:.1f} days ago)"

    return t


class SensorValuesTable(ControlNode):
    def get(self):
        now = time.time()
        
        table = []
        for name, entry in sensor_values.items():
            timestamp = entry.get('timestamp', None)
            value_raw = entry.get('value_raw', '-')
            value_cal = entry.get('value_cal', '-')        
            table.append([name, timestr(timestamp, now), value_raw, value_cal])
            
        return {
            'columns': [ 'Endpoint Name', 'Timestamp', 'Raw Value', 'Cal Value' ],
            'table': table
        }


class StatusMessagesTable(ControlNode):
    def get(self):
        now = time.time()
        
        table = []
        for timestamp, service, severity, message in status_messages:
            table.append([service, timestr(timestamp, now), severity, str(message)])
            
        return {
            'columns': ['Timestamp', 'Service Name', 'Severity', 'Message'],
            'table': table,
        }


class HeartbeatsTable(ControlNode):
    def get(self):
        now = time.time()
        
        table = []
        for key, entry in heartbeats.items():
            timestamp = entry.get('timestamp', None)
            name = entry.get('name', key)
            counts = entry.get('counts', 0)
            table.append([name, timestr(timestamp, now), counts])
            
        return {
            'columns': [ 'Name', 'Timestamp', 'Counts' ],
            'table': table,
        }

    
class RepliesTable(ControlNode):
    def get(self):
        now = time.time()
        
        table = []
        for row in replies:
            table.append([timestr(row[0], now)] + row[1:3] + [str(row[3])])
            
        return {
            'columns': ['Timestamp', 'Endpoint', 'Operation', 'Reply'],
            'table': table,
        }


ctrl.export(SensorValuesTable(), name='SensorValues.DriplineConsole')
ctrl.export(HeartbeatsTable(), name='HeartBeats.DriplineConsole')
ctrl.export(StatusMessagesTable(), name='StatusMessages.DriplineConsole')
ctrl.export(RepliesTable(), name='Replies.DriplineConsole')



async def _initialize(params):
    global dripline
    url = params.get('url', 'amqp://dripline:dripline@rabbit-broker')
    dripline = ctrl.async_dripline(url, 'SlowDripConsole')


async def _finalize():
    await dripline.aio_close()
    await asyncio.sleep(1)   # give RabbitMQ a change to perform cleanup
    
        
async def _run():
    await asyncio.gather(
        monitor_sensor_value_alerts(),
        monitor_heartbeat_alerts(),
        monitor_status_message_alerts(),
        send_heartbeats()
    )


async def monitor_sensor_value_alerts():
    while not ctrl.is_stop_requested():
        message = await dripline.sensor_value_queue().aio_get()
        if message is None or message.body is None:
            break
        _, name = message.parameters['routing_key'].split('.')
        sensor_values[name] = message.body | {
            'timestamp': message.headers.get("timestamp", None),
        }
        await ctrl.aio_publish(SensorValuesTable(), name='SensorValues.DriplineConsole')
        

async def monitor_heartbeat_alerts():
    while not ctrl.is_stop_requested():
        message = await dripline.heartbeat_queue().aio_get()
        if message is None or message.body is None:
            break
        _, name = message.parameters['routing_key'].split('.')
        counts = heartbeats.get(name, {}).get('counts', 0) + 1
        heartbeats[name] = message.body | {
            'timestamp': message.headers.get("timestamp", None),
            'counts': counts,
        }
        await ctrl.aio_publish(HeartbeatsTable(), name='HeartBeats.DriplineConsole')
        

async def monitor_status_message_alerts():
    while not ctrl.is_stop_requested():
        message = await dripline.status_message_queue().aio_get()
        if message is None or message.body is None:
            break
        _, name, severity = message.parameters['routing_key'].split('.')
        status_messages.append([
            message.headers.get("timestamp", None),
            name, severity,
            message.body
        ])
        await ctrl.aio_publish(StatusMessagesTable(), name='StatusMessages.DriplineConsole')

        
async def send_heartbeats():
    while not ctrl.is_stop_requested():
        await dripline.heartbeat_alert().aio_set(time.time())
        await dripline.status_message_alert().aio_set('I am working')
        await ctrl.aio_sleep(30)

        
async def sd_get_endpoint(endpoint:str, specifier:str=None, value:str=None, lockout_key:str=None):
    print(f'Console: GET {endpoint}')
    endpoint_node = dripline.endpoint(endpoint, specifier=specifier, lockout_key=lockout_key)
    reply = await endpoint_node.aio_get()
    replies.append([time.time(), endpoint, f'GET {specifier}: {value}', reply])
    await ctrl.aio_publish(RepliesTable(), name='Replies.DriplineConsole')

    
async def sd_set_endpoint(endpoint:str, specifier:str=None, value:str=None, lockout_key:str=None):
    print(f'Console: SET {endpoint} {value}')
    endpoint_node = dripline.endpoint(endpoint, specifier=specifier, lockout_key=lockout_key)
    reply = await endpoint_node.aio_set(value)    
    replies.append([time.time(), endpoint, f'SET {specifier}: {value}', reply])
    await ctrl.aio_publish(RepliesTable(), name='Replies.DriplineConsole')

    
async def sd_cmd_endpoint(endpoint:str, specifier:str, value:str=None, lockout_key:str=None):
    ordered_args, keyed_args = [], {}
    for v in value.split(','):
        vv = v.split('=')
        if len(vv) == 1:
            ordered_args.append(vv[0].strip())
        elif len(vv) == 2:
            keyed_args[vv[0].strip()] = vv[1].strip()    
            
    endpoint_node = dripline.endpoint(endpoint, specifier=specifier, lockout_key=lockout_key)
    reply = await endpoint_node.command(ordered_args, keyed_args).aio_get()
    
    replies.append([time.time(), endpoint, f'CMD {specifier}: {value}', reply])
    await ctrl.aio_publish(RepliesTable(), name='Replies.DriplineConsole')


    
async def _get_layout():
    return {
        "meta": { "name": "DriplineConsole" },
        "control": {
            "reload": 5,
            "grid": { "rows": 2, "columns": 2 }
        },
        "panels": [
            {
                "type": "table",
                "channel": "SensorValues.DriplineConsole",
                "title": "Sensor Values (sensor_value.* on alert exchange)"
            },
            {
                "type": "table",
                "channel": "HeartBeats.DriplineConsole",
                "title": "Heartbeats (heartbeat.* on alert exchange)"
            },
            {
                "type": "html",
                "location": "project",
                "file": "DriplineConsole",
                "title": "Endpoint Control"
            },
            {
                "type": "table",
                "channel": "Replies.DriplineConsole",
                "title": "Replies"
            },
            {
                "type": "table",
                "channel": "StatusMessages.DriplineConsole",
                "title": "Alarms (status_message.*.* on alert exchange)"
            }
        ]
    }


def _get_html():
    html = f'''
    | <form>
    |   <datalist id="dripline_endpoints">
    |     {'\n'.join(['<option value="'+name+'">' for name in sensor_values])}
    |   </datalist>
    |   <table>
    |     <tr><td>Endpoint</td><td><input name="endpoint" list="dripline_endpoints" style="width:24em"></td></tr>
    |     <tr><td>Value(s)</td><td><input name="value" style="width:24em"></td></tr>
    |     <tr><td>Specifier/Method</td><td><input name="specifier" style="width:24em" placeholder="usually this is empty"></td></tr>
    |     <tr><td>Lockout Key</td><td><input name="lockout_key" style="width:24em" placeholder="usually this is empty"></td></tr>
    |     <tr><td></td><td>
    |       <input type="submit" name="parallel DriplineConsole.sd_get_endpoint()" value="Get Value">
    |       <input type="submit" name="parallel DriplineConsole.sd_set_endpoint()" value="Set Value">
    |       <input type="submit" name="parallel DriplineConsole.sd_cmd_endpoint()" value="Send Command">
    |     </td></tr>
    |   </table>
    |   <!--
    |   <span style="margin-left:1rem">Replies</span>
    |   <div style="width:80%;height:8rem;margin-left:2rem;border:thin solid gray"></div>
    |   -->
    | </form>
    '''
    return re.sub('^[ ]*\\|', '', html, flags=re.MULTILINE)



if __name__ == '__main__':
    from slowpy.dash import Tasklet
    Tasklet().run()
