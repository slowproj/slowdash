# Created by Sanshiro Enomoto on 3 October 2025 #

import os, time, datetime, socket, getpass, uuid, json

from slowpy.control import ControlNode, ControlVariableNode, control_system as ctrl
ctrl.import_control_module('AsyncRabbitMQ')



sender_info = {
    'exe': __file__,
    'hostname': socket.gethostname(),
    'service_name': 'slowdrip',
    'username': getpass.getuser(),
    'versions': {
        'slowdash': {
            'package': 'slowdash',
            'version': '0',
            'commit': '0',
        }
    }
}


class DriplineNode(ControlNode):
    def __init__(self, rabbitmq_url:str, name:str=None):
        self.rmq = ctrl.rabbitmq(rabbitmq_url)
        self.name = name or f'SlowDash_{socket.gethostname()}_{os.getpid()}'
        self.sender_id = str(uuid.uuid4())
        
        self.alerts_exchange = self.rmq.topic_exchange('alerts')
        self.requests_exchange = self.rmq.topic_exchange('requests')
                
        self.reply_queue_node = None            # to be set by endpoint()
        self.request_queue_node = None          # to be set by request()
        self.sensor_value_queue_node = None     # to be set by self.sensors_value_queue()
        self.heartbeat_queue_node = None        # to be set by self.heartbeat_queue()
        self.status_message_queue_node = None   # to be set by self.status_message_queue()
        
        
    async def aio_close(self):
        if self.rmq is not None:
            await self.rmq.aio_close()
        self.rmq = None
        
        
    ## child nodes ##
    # dripline().endpoint(name): set/get to other dripline endpoints
    def endpoint(self, name:str):
        return EndpointNode(self, name)

    # dripline().request(): handles set/get/cmd requests from other dripline services
    def request(self, handler):
        return RequestNode(self, handler)

    # dripline().sensor_value_alert(): sends sensor_value alert; use aio_set(value)
    def sensor_value_alert(self, name:str=None):
        return SensorValueAlertNode(self, name)

    # dripline().heartbeat_alert(): sends heartbeat alerts; use aio_set(value)
    def heartbeat_alert(self):
        return HeartbeatAlertNode(self)

    # dripline().status_message_alert(): sends status_message alerts; use aio_set(value)
    def status_message_alert(self, message_type='notice'):
        return StatusMessageAlertNode(self, message_type)

    # dripline().sensor_value_queue(): receives sensor_value; use aio_get()
    def sensor_value_queue(self):
        return SensorValuesQueueNode(self)

    # dripline().heartbeat_queue(): receives heartbeat; use aio_get()
    def heartbeat_queue(self):
        return HeartbeatQueueNode(self)

    # dripline().status_message_queue(): receives status_messages; use aio_get()
    def status_message_queue(self):
        return StatusMessageQueueNode(self)

    # dripline().service(server):
    def service(self, server, *, endpoints:list[str]|None=None):
        return ServiceNode(self, server, endpoints=endpoints)

    
    @classmethod
    def _node_creator_method(cls):
        def dripline(self, *args, **kwargs):
            if True:
                return DriplineNode(*args, **kwargs)
            
            try:
                self.dripline_node
            except:
                self.dripline_node = DriplineNode(*args, **kwargs)

            return self.dripline_node

        return dripline


    
class EndpointNode(ControlNode):
    def __init__(self, dripline:DriplineNode, name:str, *, specifier:str=None, lockout_key:str=None, timeout=None):
        self.specifier = specifier or ''
        self.lockout_key = lockout_key or '00000000-0000-0000-0000-000000000000'
        
        if dripline.reply_queue_node is None:
            dripline.reply_queue_node = (
                dripline.requests_exchange.queue(f'{dripline.name}_reply', timeout=(timeout or 30), exclusive=True)
            )
        self.reply_queue_node = dripline.reply_queue_node
        self.routing_key = name

                
    async def aio_set(self, value):
        operation_code = 0  # 0: Set, 1: Get, 9: Command
        body={ 'values': [value] }
        return await self.aio_do_send_request(operation_code, body)

    
    async def aio_get(self):
        operation_code = 1  # 0: Set, 1: Get, 9: Command
        body = {}
        return await self.aio_do_send_request(operation_code, body)

    
    ## child nodes ##
    # dripline().endpoint(name).value_raw(): aio_get() returns 'value_raw'
    def value_raw(self):
        return RawValueNode(self)

    # dripline().endpoint(name).value_cal(): aio_get() returns 'value_cal'
    def value_cal(self):
        return CalibratedValueNode(self)

    # dripline().endpoint(name).command(*args,**kwargs): aio_get() sends a command to other endpoints
    def command(self, *args, **kwargs):
        return EndpointCommandNode(self, *args, **kwargs)


    async def aio_do_send_request(self, operation_code:int, body):
        now = datetime.datetime.fromtimestamp(time.time(), tz=datetime.timezone.utc)

        headers = {
            'message_operation': operation_code,  # 0: Set, 1: Get, 9: Command
            'message_type': 3,  # 2: Reply, 3: Request, 4: Alert
            'lockout_key': self.lockout_key,
            'specifier': self.specifier,
            'timestamp': now.isoformat().replace('+00:00', 'Z'),
            'sender_info': sender_info,
        }
        parameters = {
            'message_id': f'{uuid.uuid4()}/0/1',
            'content_encoding': 'application/json',
        }

        message = await self.reply_queue_node.rpc_call(self.routing_key, body, headers, parameters).aio_get()
        if type(message.body) is dict:
            return message.body
        else:
            return json.loads(message.body or '{}')
    

    
class EndpointCommandNode(ControlVariableNode):
    def __init__(self, endpoint:EndpointNode, *args, **kwargs):
        self.endpoint_node = endpoint_node
        self.body = {'values': [ arg for arg in args ] }
        self.body.update({ k:v for k,v in kwargs.items() })
        
        
    async def aio_get(self):
        operation_code = 9  # 0: Set, 1: Get, 9: Command
        return await self.endpoint_node.aio_do_send_request(operation_code, self.body)

    
        
class RawValueNode(ControlNode):
    def __init__(self, endpoint:EndpointNode):
        self.endpoint = endpoint
            
    async def aio_set(self, value):
        return await self.endpoint.aio_set(value)
    
    async def aio_get(self):
        return (await self.endpoint.aio_get()).get('value_raw', None)

    
    
class CalibratedValueNode(ControlNode):
    def __init__(self, endpoint:EndpointNode):
        self.endpoint = endpoint
            
    async def aio_get(self):
        return (await self.endpoint.aio_get()).get('value_cal', None)


    
class RequestNode(ControlNode):
    def __init__(self, dripline:DriplineNode, handler):
        self.handler = handler
        
        if dripline.request_queue_node is None:
            dripline.request_queue_node = (
                dripline.requests_exchange.queue(f'{dripline.name}', exclusive=True)
            )
        self.request_queue_node = dripline.request_queue_node

    
    async def aio_get(self):
        return await self.request_queue_node.rpc_function(self.handler).aio_get()


    
class SensorValueAlertNode(ControlNode):
    def __init__(self, dripline:DriplineNode, name:str=None):
        self.name = name or dripline.name
        self.sender_id = dripline.sender_id
        self.publish_node = dripline.alerts_exchange.publish(f'sensor_value.{self.name}')

        
    async def aio_set(self, value):
        now = datetime.datetime.fromtimestamp(time.time(), tz=datetime.timezone.utc)

        if type(value) is tuple and len(value) >= 2:
            body = { 'value_raw': value[0], 'value_cal': value[1] }
        elif type(value) is dict:
            body = value
        elif type(value) in [ bool, int, float, str ]:
            body = { 'value_raw': value }
        else:
            # throw an error?
            body = value
            
        headers = {
            'message_type': 4,  # 2: Reply, 3: Request, 4: Alert
            'timestamp': now.isoformat().replace('+00:00', 'Z'),
            'sender_info': sender_info,
        }
        parameters = {
            'message_id': f'{uuid.uuid4()}/0/1',
            'content_encoding': 'application/json',
        }
        
        return await self.publish_node.aio_set((body, headers, parameters))

    

class HeartbeatAlertNode(ControlNode):
    def __init__(self, dripline:DriplineNode):
        self.name = dripline.name
        self.sender_id = dripline.sender_id
        self.publish_node = dripline.alerts_exchange.publish(f'heartbeat.{self.name}')

        
    async def aio_set(self, value):
        now = datetime.datetime.fromtimestamp(value or time.time(), tz=datetime.timezone.utc)
        
        body = {
            'id': self.sender_id,
            'name': self.name,
        }
        headers = {
            'message_type': 4,  # 2: Reply, 3: Request, 4: Alert
            'timestamp': now.isoformat().replace('+00:00', 'Z'),
            'sender_info': sender_info,
        }
        parameters = {
            'message_id': f'{uuid.uuid4()}/0/1',
            'content_encoding': 'application/json',
        }
        
        return await self.publish_node.aio_set((body, headers, parameters))

    

class StatusMessageAlertNode(ControlNode):
    def __init__(self, dripline:DriplineNode, message_type='notice'):
        self.name = dripline.name
        self.sender_id = dripline.sender_id
        self.publish_node = dripline.alerts_exchange.publish(f'status_message.{self.name}.{message_type}')

        
    async def aio_set(self, value):
        now = datetime.datetime.fromtimestamp(time.time(), tz=datetime.timezone.utc)
        
        body = {
            'message': value,
        }
        headers = {
            'message_type': 4,  # 2: Reply, 3: Request, 4: Alert
            'timestamp': now.isoformat().replace('+00:00', 'Z'),
            'sender_info': sender_info,
        }
        parameters = {
            'message_id': f'{uuid.uuid4()}/0/1',
            'content_encoding': 'application/json',
        }
        
        return await self.publish_node.aio_set((body, headers, parameters))

    

class SensorValuesQueueNode(ControlNode):
    def __init__(self, dripline:DriplineNode):
        if dripline.sensor_value_queue_node is None:
            dripline.sensor_value_queue_node = (
                dripline.alerts_exchange.queue(f'{dripline.name}_sensor_value', routing_key='sensor_value.*', exclusive=True)
            )
        self.queue_node = dripline.sensor_value_queue_node

    
    async def aio_get(self):
        message = await self.queue_node.aio_get()
        if message[0] is None or type(message[0]) is dict:
            return message
        else:
            # Dripline puts content_type in the content_encoding fields, causing unparsed results
            return type(message)(json.loads(message[0] or '{}'), *message[1:])

    
    
class HeartbeatQueueNode(ControlNode):
    def __init__(self, dripline:DriplineNode):
        if dripline.heartbeat_queue_node is None:
            dripline.heartbeat_queue_node = (
                dripline.alerts_exchange.queue(f'{dripline.name}_heartbeat', routing_key='heartbeat.*', exclusive=True)
            )
        self.queue_node = dripline.heartbeat_queue_node

    
    async def aio_get(self):
        message = await self.queue_node.aio_get()
        if message[0] is None or type(message[0]) is dict:
            return message
        else:
            # Dripline puts content_type in the content_encoding fields, causing unparsed results
            return type(message)(json.loads(message[0] or '{}'), *message[1:])


    
class StatusMessageQueueNode(ControlNode):
    def __init__(self, dripline:DriplineNode):
        if dripline.status_message_queue_node is None:
            dripline.status_message_queue_node = (
                dripline.alerts_exchange.queue(f'{dripline.name}_status_message', routing_key='status_message.*.*', exclusive=True)
            )
        self.queue_node = dripline.status_message_queue_node

    
    async def aio_get(self):
        message = await self.queue_node.aio_get()
        if message[0] is None or type(message[0]) is dict:
            return message
        else:
            # Dripline puts content_type in the content_encoding fields, causing unparsed results
            return type(message)(json.loads(message[0] or '{}'), *message[1:])



class ServiceNode(ControlNode):
    def __init__(self, dripline:DriplineNode, server, *, endpoints:list[str]|None=None):
        self.dripline_node = dripline
        self.server = server
        self.endpoints = list(endpoints or [])
        
        self.request_queue_node = dripline.requests_exchange.queue(name=dripline.name, routing_key='*', exclusive=True)

    
    async def aio_start(self):
        while not ctrl.is_stop_requested():
            await self.request_queue_node.rpc_function(self._handle_message).aio_get()
    

    async def _handle_message(self, message):
        print(message)
        operation = message.headers.get('message_operation', -1)
        print(f'REQUEST: op={operation}, body={message.body}')
        return {'status': 'handled', 'request': message.body}
        
