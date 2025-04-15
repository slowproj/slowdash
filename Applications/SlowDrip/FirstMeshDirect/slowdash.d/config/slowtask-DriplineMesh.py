

import asyncio, json, re, datetime, time, logging
import aio_pika

from slowpy.control import ControlSystem, ControlNode
ctrl = ControlSystem()

endpoint_values = {}
heartbeat_values = {}


import slowlette
webapi = slowlette.Slowlette()

@webapi.get('/api/config/contentlist')
def add_slowplot_PlotLayoutOverride():
    return [ { "type": "html", "name": "EndpointSet" } ]


@webapi.get('/api/config/content/html-EndpointSet')
def html_EndpointSet(request:slowlette.Request):
    request.abort()

    html = f'''
    | <form>
    |   <datalist id="dripline_endpoints">
    |     {'\n'.join(['<option value="'+name+'">' for name in endpoint_values])}
    |   </datalist>
    |   <table>
    |     <tr><td>Endpoint</td><td><input name="endpoint" list="dripline_endpoints" style="width:32em"></td></tr>
    |     <tr><td>Value/Command</td><td><input name="value" style="width:32em"></td></tr>
    |     <tr><td></td><td>
    |       <input type="submit" name="set_endpoint" value="Set Value">
    |       <input type="submit" name="cmd_endpoint" value="Send Command">
    |     </td></tr>
    |   </table>
    | </form>
    '''
    html = re.sub('^[ ]*\\|', '', html, flags=re.MULTILINE)

    return slowlette.Response(200, content_type='text/html', content=html)



def timestr(timestamp, now):
    if timestamp is not None:
        unix_time = datetime.datetime.fromisoformat(timestamp).timestamp()
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
    else:
        t= '-'

    return t



class EndpointsNode(ControlNode):
    def get(self):
        now = time.time()
        
        table = []
        for name, entry in endpoint_values.items():
            timestamp = entry.get('timestamp', None)
            value_raw = entry.get('value_raw', '-')
            value_cal = entry.get('value_cal', '-')        
            table.append([name, timestr(timestamp, now), value_raw, value_cal])
            
        return {
            'columns': [ 'Endpoint Name', 'Timestamp', 'Raw Value', 'Cal Value' ],
            'table': table
        }

    

class HeartbeatsNode(ControlNode):
    def get(self):
        now = time.time()
        
        table = []
        for name, entry in heartbeat_values.items():
            timestamp = entry.get('timestamp', None)
            table.append([name, timestr(timestamp, now)])
            
        return {
            'columns': [ 'Name', 'Timestamp' ],
            'table': table
        }

    
def _export():
    return [
        ('CurrentEndpointValues', EndpointsNode()),
        ('HeartBeats', HeartbeatsNode()),
    ]



def _process_command(doc):
    if doc.get('set_endpoint', False):
        endpoint = doc.get('endpoint', None)
        value = doc.get('endpoint', None)
        if (endpoint is None) or (value is None):
            return False
        send_set_request(endpoint, value)
        
    elif doc.get('cmd_endpoint', False):
        endpoint = doc.get('endpoint', None)
        value = doc.get('endpoint', None)
        if (endpoint is None) or (value is None):
            return False
        send_cmd_request(endpoint, value)
        
    else:
        return None

    
    return True



connection, channel, queue = None, None, None

        
async def _initialize(params):
    global connection, channel, queue
    connection = await aio_pika.connect_robust('amqp://dripline:dripline@localhost')
    channel = await connection.channel()
    
    alerts_exchange = await channel.declare_exchange('alerts', aio_pika.ExchangeType.TOPIC)
    requests_exchange = await channel.declare_exchange('requests', aio_pika.ExchangeType.TOPIC)
    queue = await channel.declare_queue(name='slowdash', exclusive=True)
    await queue.bind(alerts_exchange, routing_key='sensor_value.*')
    await queue.bind(alerts_exchange, routing_key='heartbeat.*')


async def _finalize():
    global connection, channel, queue
    if connection:
        await connectin.close()
        connection = None
    
        
async def _run():
    global connection, channel, queue

    while not ctrl.is_stop_requested():
        try:
            message = await queue.get()
            async with message.process():
                on_message(message)
        except aio_pika.exceptions.QueueEmpty:
            await asyncio.sleep(0.5)


            
def send_set_request(endpoint, value):
    message_id = f'{uuid.uuid4()}/0/1'
    channel.basic_publish(
        routing_key='peaches',
        exchange='requests',
        properties=pika.BasicProperties(
            message_id = message_id,
            reply_to = 'slowdash',
            content_encoding = 'application/json',
            correlation_id = message_id,
            timestamp = int(time.time()),
            headers={
                'message_type': 3,  # 2: Reply, 3: Request, 4: Alert
                'message_operation': 1,  # 0: Set, 1: Get, 9: Command
                
                'specifier': '',
                'timestamp': '2025-04-04T05:46:19.937387Z',
                'sender_info': {
                    'exe': '/usr/local/bin/python3.12',
                    'hostname': '16cfe7cb4ded',
                    'service_name': 'unknown',
                    'username': 'root',
                    'versions': {
                        'dripline': {
                            'version': '3.0.0'
                        },
                        'dripline-cpp': {
                            'commit': '5ee205622d6ba8ce5da9e1cfb52b726a99b3cc49',
                            'package': 'driplineorg/dripline-cpp',
                            'version': '2.10.0'
                        },
                        'dripline-python': {
                            'commit': 'na',
                            'package': 'driplineorg/dripline-python',
                            'version': '5.0.0'
                        }
                    }
                },
            },
        ),
        body=b'{"values":[10.0]}'
    )

    
def send_cmd_request(endpoint, value):
    pass
    

def on_message(message):
    global endpoint_values, heartbeat_values
    
    name = message.routing_key
    record = {
        'timestamp': message.headers.get("timestamp", None),
    }
    record.update(json.loads(message.body.decode()))

    if name.startswith('sensor_value.'):
        name = name[13:]
        endpoint_values[name] = record
    elif name.startswith('heartbeat.'):
        name = name[10:]
        heartbeat_values[name] = record
    else:
        return

    
                
if __name__ == '__main__':
    async def main():
        _initialize({})
        _run()
        _finalize()

    ControlSystem.stop_by_signal()
    asyncio.run(main())
