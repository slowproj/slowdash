# Created by Sanshiro Enomoto on 13 March 2026 #

import queue
from slowpy.control import ControlNode, ControlException

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class MQTTNode(ControlNode):
    def __init__(self, host:str, port:int=1883):
        self.host = host
        self.port = port
        self.keepalive = 60

        self.subscribers: dict[str,list[SubscribeNode]] = {}
        
        import paho.mqtt.client as mqtt
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

        def on_connect(client, userdata, flags, response_code, properties):
            logger.info(f'MQTT broker connected: {response_code}')
        self.client.on_connect = on_connect
    
        try:
            self.client.connect(self.host, self.port, keepalive=self.keepalive)
        except Exception as e:
            logger.error(f'Unable to connect to MQTT Broker:  {host}:{port}: {e}')
            self.client = None

        if self.client:
            self.client.loop_start()


    def __del__(self):
        self.close()

        
    def close(self):
        if self.client is None:
            return
        
        self.client.loop_stop()
        del self.client
        self.client = None
        logger.info(f'MQTT Connection Closed')

        
    def publish(self, topic):
        return PublishNode(self, topic)


    def subscribe(self, topic, handler=None):
        return SubscribeNode(self, topic, handler)


    def do_subscribe(self, topic_filter:str, subscribe_node):
        def mqtt_callback(client, userdata, msg):
            topic, message = str(msg.topic), msg.payload.decode()
            logger.debug(f'MQTT message: {msg.topic}: {msg.payload.decode()}')
            for subscriber in self.subscribers.get(topic_filter, []):
                subscriber.handler(topic, message)

        if topic_filter not in self.subscribers:
            self.subscribers[topic_filter] = []
            self.client.message_callback_add(topic_filter, mqtt_callback)
            self.client.subscribe(topic_filter)

        self.subscribers[topic_filter].append(subscribe_node)

        
    @classmethod
    def _node_creator_method(cls):
        def mqtt(self, host:str, port:int=1883):
            if True:
                return MQTTNode(host, port)
            
            name = '%s:%s' % (host, str(port))
            try:
                self._mqtt_nodes.keys()
            except:
                self._mqtt_nodes = {}
            node = self._mqtt_nodes.get(name, None)
        
            if node is None:
                node = MQTTNode(host, port)
                self._mqtt_nodes[name] = node

            return node

        return mqtt

    
    
class PublishNode(ControlNode):
    def __init__(self, mqtt, topic):
        self.mqtt = mqtt
        self.topic = topic

        
    def set(self, value):
        if self.mqtt.client is None:
            return None

        self.mqtt.client.publish(self.topic, value)
        

        
class SubscribeNode(ControlNode):
    def __init__(self, mqtt:MQTTNode, topic_filter:str, handler=None):
        """
        - If handler is not None, it is called on receiving a message.
        - Otherwise, the received messages are queued, which can be retrieved by has_data()/get()
        """
        
        self.queue = queue.Queue(maxsize=1024)
        
        def default_handler(topic, message):
            self.queue.put(message, block=True, timeout=None)
        self.handler = handler or default_handler

        mqtt.do_subscribe(topic_filter, self)

        
    def has_data(self):
        return not self.queue.empty()

        
    def get(self):
        return self.queue.get(block=True, timeout=None)


    def do_handle_message(self, topic, message):
        return self.queue.get(block=True, timeout=None)


    
if __name__ == '__main__':
    """
    Chat example
    """
    
    import sys
    from slowpy.control import control_system as ctrl
    mqtt = ctrl.import_control_module('MQTT').mqtt('localhost')

    def handler(topic, message):
        sys.stdout.write(f'\n{message}\n> ')
    mqtt.subscribe('chat/#', handler)
        
    while True:
        try:
            line = input('> ')
        except (EOFError, KeyboardInterrupt):
            break
        mqtt.publish('chat/all').set(line)

    mqtt.close()
