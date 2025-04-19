

import asyncio, json, re, uuid, datetime, time, socket, getpass, logging
import aio_pika

from slowpy.control import ControlSystem, ControlNode
ctrl = ControlSystem()

endpoint_values = {}
heartbeat_values = {}
status_messages = []
requests = []
replies = []


sender_info = {
    'exe': __file__,
    'hostname': socket.gethostname(),
    'service_name': 'slowdash',
    'username': getpass.getuser(),
    'versions': {
        'slowdash': {
            'package': 'slowdash',
            'version': '0',
            'commit': '0',
        }
    }
}



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
    |     <tr><td>Specifier</td><td><input name="specifier" style="width:32em"></td></tr>
    |     <tr><td>Lockout Key</td><td><input name="lockout_key" style="width:32em"></td></tr>
    |     <tr><td></td><td>
    |       <input type="submit" name="get_endpoint" value="Get Value">
    |       <input type="submit" name="set_endpoint" value="Set Value">
    |       <input type="submit" name="cmd_endpoint" value="Send Command">
    |     </td></tr>
    |   </table>
    |   <!--
    |   <span style="margin-left:1rem">Replies</span>
    |   <div style="width:80%;height:8rem;margin-left:2rem;border:thin solid gray"></div>
    |   -->
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
            'table': table,
        }

    
class StatusMessagesNode(ControlNode):
    def get(self):
        return {
            'columns': ['Timestamp', 'Service Name', 'Severity', 'Message'],
            'table': status_messages,
        }


    
class RequestsNode(ControlNode):
    def get(self):
        return {
            'columns': ['Timestamp', 'Sender Name', 'Request'],
            'table': requests,
        }

    
class RepliesNode(ControlNode):
    def get(self):
        return {
            'columns': ['Timestamp', 'Endpoint', 'Operation', 'Reply'],
            'table': replies,
        }

    
def _export():
    return [
        ('CurrentEndpointValues', EndpointsNode()),
        ('HeartBeats', HeartbeatsNode()),
        ('StatusMessages', StatusMessagesNode()),
        ('Requests', RequestsNode()),
        ('Replies', RepliesNode()),
    ]



async def _process_command(doc):
    if doc.get('get_endpoint', False):
        endpoint = doc.get('endpoint', None)
        if (endpoint is None):
            return False
        await send_get_request(endpoint)
        
    elif doc.get('set_endpoint', False):
        endpoint = doc.get('endpoint', None)
        value = doc.get('value', None)
        if (endpoint is None) or (value is None):
            return False
        await send_set_request(endpoint, value)
        
    elif doc.get('cmd_endpoint', False):
        endpoint = doc.get('endpoint', None)
        value = doc.get('value', None)
        if (endpoint is None) or (value is None):
            return False
        
        ordered_args, keyed_args = [], {}
        for v in value.split(','):
            vv = v.split('=')
            if len(vv) == 1:
                ordered_args.append(vv[0].strip())
            elif len(vv) == 2:
                keyed_args[vv[0].strip()] = vv[1].strip()
            
        await send_cmd_request(endpoint, ordered_args, keyed_args)
        
    else:
        return None

    
    return True



connection, channel = None, None
alerts_exchange, requests_exchange = None, None
request_queue, reply_queue, alert_queue = None, None, None
        
async def _initialize(params):
    global connection, channel
    global alerts_exchange, requests_exchange
    global request_queue, reply_queue, alert_queue
    
    connection = await aio_pika.connect_robust('amqp://dripline:dripline@localhost')
    channel = await connection.channel()
    
    alerts_exchange = await channel.declare_exchange('alerts', aio_pika.ExchangeType.TOPIC)
    alert_queue = await channel.declare_queue(name='slowdash_subscribe', exclusive=True)
    await alert_queue.bind(alerts_exchange, routing_key='sensor_value.*')
    await alert_queue.bind(alerts_exchange, routing_key='heartbeat.*')
    await alert_queue.bind(alerts_exchange, routing_key='status_message.*.*')
    
    requests_exchange = await channel.declare_exchange('requests', aio_pika.ExchangeType.TOPIC)
    request_queue = await channel.declare_queue(name='slowdash', exclusive=True)
    reply_queue = await channel.declare_queue(name='slowdash_reply', exclusive=True)
    await request_queue.bind(requests_exchange, routing_key=request_queue.name)
    await reply_queue.bind(requests_exchange, routing_key=reply_queue.name)


async def _finalize():
    global connection
    if connection:
        await connection.close()
        connection = None
    
        
async def _run():
    requests_task = asyncio.create_task(handle_requests())
    alerts_task = asyncio.create_task(handle_alerts())
    await asyncio.gather(requests_task, alerts_task)

    
async def handle_requests():
    while not ctrl.is_stop_requested():
        try:
            message = await request_queue.get()
            async with message.process():
                await on_request_message(message)
        except aio_pika.exceptions.QueueEmpty:
            await asyncio.sleep(0.5)


async def handle_alerts():
    while not ctrl.is_stop_requested():
        try:
            message = await alert_queue.get()
            async with message.process():
                await on_alert_message(message)
        except aio_pika.exceptions.QueueEmpty:
            await asyncio.sleep(0.5)

            

async def on_request_message(message):
    request_time = time.time()
    message_id = f'{uuid.uuid4()}/0/1'
    timestamp = datetime.datetime.fromtimestamp(request_time, tz=datetime.timezone.utc).isoformat().replace('+00:00', 'Z')
    op_name = {'0':'SET', '1':'GET', '9':'CMD'}.get(str(message.headers.get('message_operation', 2)), 'INVALID')
    sender = message.headers.get('sender_info', {}).get('service_name', None) or message.reply_to
    
    requests.append([timestamp, sender, f'{op_name}: {message.body.decode()}'])
    
    await requests_exchange.publish(
        aio_pika.Message(
            correlation_id = message.correlation_id,
            content_encoding = 'application/json',
            message_id = message_id,
            headers = {
                'message_type': 2,  # 2: Reply, 3: Request, 4: Alert
                'timestamp': timestamp,
                'sender_info': sender_info,
                'return_code': 0,
                'return_message': 'Success',
            },
            body = b'{"message": "request received"}',
        ),
        routing_key = message.reply_to
    )
    
    
async def on_alert_message(message):
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
    elif name.startswith('status_message.'):
        keys = name.split('.')
        status_messages.append([
            message.headers.get("timestamp", None),
            keys[1], keys[2],
            message.body.decode()
        ])
    else:
        return

    
                
            

async def send_get_request(endpoint, **kwargs):
    return await send_request(1, routing_key=endpoint, body='{}', **kwargs)
    
async def send_set_request(endpoint, value, **kwargs):
    return await send_request(0, routing_key=endpoint, body='{"values":[%s]}'%str(value), **kwargs)

async def send_cmd_request(endpoint, ordered_args=None, keyed_args=None, **kwargs):
    payload = {'values': [] if ordered_args is None else ordered_args}
    payload.update({} if keyed_args is None else keyed_args)
    return await send_request(9, routing_key=endpoint, body=json.dumps(payload), **kwargs)
    

async def send_request(operation, routing_key, body, *, specifier=None, lockout_key=None):
    if specifier is None:
        specifier = ''
    if lockout_key is None:
        lockout_key = '00000000-0000-0000-0000-000000000000'
        
    request_time = time.time()
    message_id = f'{uuid.uuid4()}/0/1'
    correlation_id = f'{uuid.uuid4()}'
    timestamp = datetime.datetime.fromtimestamp(request_time, tz=datetime.timezone.utc).isoformat().replace('+00:00', 'Z')
    
    await requests_exchange.publish(
        aio_pika.Message(
            reply_to = reply_queue.name,
            correlation_id = correlation_id,
            content_encoding = 'application/json',
            message_id = message_id,
            headers = {
                'message_operation': operation,  # 0: Set, 1: Get, 9: Command
                'message_type': 3,  # 2: Reply, 3: Request, 4: Alert
                'lockout_key': lockout_key,
                'specifier': specifier,
                'timestamp': timestamp,
                'sender_info': sender_info,
            },
            body = body.encode()
        ),
        routing_key=routing_key
    )

    date = datetime.datetime.fromtimestamp(request_time).strftime('%y-%m-%d %H:%M:%S')
    op_name = {'0':'SET', '1':'GET', '9':'CMD'}.get(str(operation), 'UNKNOWN')
    while True:
        try:
            message = await reply_queue.get()
            async with message.process():
                reply = message.body.decode()
                replies.append([date, routing_key, f'{op_name}: {body}', reply])
                return reply
        except aio_pika.exceptions.QueueEmpty:
            await asyncio.sleep(0.5)
        if time.time() - request_time > 5:
            replies.append([date, routing_key, f'{op_name}: {body}', '**TIMEOUT**'])
            return None

            
    
if __name__ == '__main__':
    async def main():
        await _initialize({})
        await _run()
        await _finalize()

    ControlSystem.stop_by_signal()
    asyncio.run(main())
