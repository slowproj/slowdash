

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
    |       <input type="submit" name="cmd_endpoint" value="Command">
    |     </td></tr>
    |   </table>
    | </form>
    '''
    
    return slowlette.Response(200, content_type='text/html', content=re.sub('^[ ]*\\|', '', html, flags=re.MULTILINE))



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
    


        
async def _run():
    connection = await aio_pika.connect_robust('amqp://dripline:dripline@localhost')
    async with connection:
        channel = await connection.channel()
        alerts_exchange = await channel.declare_exchange('alerts', aio_pika.ExchangeType.TOPIC)
        requests_exchange = await channel.declare_exchange('requests', aio_pika.ExchangeType.TOPIC)
        queue = await channel.declare_queue(name='slowdash', exclusive=True)
        await queue.bind(alerts_exchange, routing_key='sensor_value.*')
        await queue.bind(alerts_exchange, routing_key='heartbeat.*')

        while not ctrl.is_stop_requested():
            try:
                message = await queue.get()
                async with message.process():
                    on_message(message)
            except aio_pika.exceptions.QueueEmpty:
                await asyncio.sleep(0.5)


                
if __name__ == '__main__':                    
    ControlSystem.stop_by_signal()
    asyncio.run(_run())
