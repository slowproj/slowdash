# Created by Sanshiro Enomoto on 12 October 2025 #

'''
This is a reduced no-async version of control_AsyncDripline.py.
- This implementes only dripline().endpoint(). For all the other features, the async version should be used.
- The selected features are basicay copy from the async version, with:
  - implementing set()/get() instead of aio_set()/aio_get(),
  - importing 'control_RabbitMQ.py' instead of 'control_AsyncRabbitMQ.py',
  - using RabbitMQ set()/get() instead of aio_set()/aio_get() with dropping "await", and
  - adding auto-reconnect as connection can be closed by broker due to missing heartbeats.
- Maybe other features can be included, but this will require users to pay attention to concurrency.
'''


import os, time, datetime, socket, getpass, uuid, json

from slowpy.control import ControlNode, ControlVariableNode, control_system as ctrl
ctrl.import_control_module('RabbitMQ')



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
        self.rmq = ctrl.rabbitmq(rabbitmq_url, heartbeat=300)
        self.name = name or f'SlowDash_{socket.gethostname()}_{os.getpid()}'
        self.sender_id = str(uuid.uuid4())
        
        self.alerts_exchange = self.rmq.topic_exchange('alerts')
        self.requests_exchange = self.rmq.topic_exchange('requests')                
        self.reply_queue_node = None            # to be set by endpoint()
        
        
    ## child nodes ##
    # dripline().endpoint(name): set/get to other dripline endpoints
    def endpoint(self, name:str):
        return EndpointNode(self, name)

    # dripline().sensor_value_alert(): sends sensor_value alert; use set(value)
    def sensor_value_alert(self, name:str=None):
        return SensorValueAlertNode(self, name)

    
    @classmethod
    def _node_creator_method(cls):
        def dripline(self, *args, **kwargs):
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

                
    def set(self, value):
        operation_code = 0  # 0: Set, 1: Get, 9: Command
        body={ 'values': [value] }
        return self.do_send_request(operation_code, body)

    
    def get(self):
        operation_code = 1  # 0: Set, 1: Get, 9: Command
        body = {}
        return self.do_send_request(operation_code, body)

    
    ## child nodes ##
    # dripline().endpoint(name).value_raw(): get() returns 'value_raw'
    def value_raw(self):
        return RawValueNode(self)

    # dripline().endpoint(name).value_cal(): get() returns 'value_cal'
    def value_cal(self):
        return CalibratedValueNode(self)

    # dripline().endpoint(name).command(*args,**kwargs): get() sends a command to other endpoints
    def command(self, *args, **kwargs):
        return EndpointCommandNode(self, *args, **kwargs)

    
    def do_send_request(self, operation_code:int, body):
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

        message = self.reply_queue_node.rpc_call(self.routing_key, body, headers, parameters).get()
        
        return json.loads(message.body or '{}')
    

    
class EndpointCommandNode(ControlNode):
    def __init__(self, endpoint:EndpointNode, *args, **kwargs):
        self.endpoint_node = endpoint_node
        self.body = {'values': [ arg for arg in args ] }
        self.body.update({ k:v for k,v in kwargs.items() })
        
        
    def get(self):
        operation_code = 9  # 0: Set, 1: Get, 9: Command
        return self.endpoint_node.do_send_request(operation_code, self.body)


    
class RawValueNode(ControlVariableNode):
    def __init__(self, endpoint:EndpointNode):
        self.endpoint = endpoint
            
    def set(self, value):
        self.endpoint.set(value)
    
    def get(self):
        return self.endpoint.get().get('value_raw', None)

    
    
class CalibratedValueNode(ControlNode):
    def __init__(self, endpoint:EndpointNode):
        self.endpoint = endpoint
            
    def get(self):
        return self.endpoint.get().get('value_cal', None)



class SensorValueAlertNode(ControlNode):
    def __init__(self, dripline:DriplineNode, name:str=None):
        self.name = name or dripline.name
        self.sender_id = dripline.sender_id
        self.publish_node = dripline.alerts_exchange.publish(f'sensor_value.{self.name}')

        
    def set(self, value):
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
        
        return self.publish_node.set((body, headers, parameters))
    
