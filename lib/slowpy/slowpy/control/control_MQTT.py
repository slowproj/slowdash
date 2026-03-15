# Created by Sanshiro Enomoto on 13 March 2026 #

import queue, logging
from slowpy.control import ControlNode, ControlException


class MQTTNode(ControlNode):
    def __init__(self, host:str, port:int=1883):
        self.host = host
        self.port = port
        self.keepalive = 60

        self.subscribers: dict[str,list[SubscribeNode]] = {}
        
        import paho.mqtt.client as mqtt
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

        def on_connect(client, userdata, flags, response_code, properties):
            logging.info(f'MQTT server connected: {response_code}')

        def on_message(client, userdata, msg):
            logging.debug(f'MQTT message: {msg.topic}: {msg.payload.decode()}')
            topic, message = msg.topic, msg.payload.decode()
            for subscriber in self.subscribers.get(topic, []):
                subscriber.do_handle(message)
    
        self.client.on_connect = on_connect
        self.client.on_message = on_message
    
        try:
            self.client.connect(self.host, self.port, keepalive=self.keepalive)
        except Exception as e:
            logging.error(f'Unable to connect to MQTT Broker:  {host}:{port}: {e}')
            self.client = None

        if self.client:
            self.client.loop_start()


    def __del__(self):
        self.close()
        logging.info(f'MQTT Connection Closed')

        
    def close(self):
        if self.client:
            self.client.loop_stop()
        del self.client
        self.client = None

        
    def publish(self, topic):
        return PublishNode(self, topic)


    def subscribe(self, topic, handler=None):
        return SubscribeNode(self, topic, handler)


    def do_subscribe(self, topic, subscribe_node):
        if not self.client:
            return

        if topic not in self.subscribers:
            self.client.subscribe(topic)
            self.subscribers[topic] = []
            
        self.subscribers[topic].append(subscribe_node)
        

        
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
    def __init__(self, mqtt:MQTTNode, topic:str, handler=None):
        """
        - If handler is not None, it is called on receiving a message.
        - Otherwise, the received messages are queued, which can be retrieved by has_data()/get()
        """
        
        self.queue = queue.Queue(maxsize=1024)
        def default_handler(message):
            self.queue.put(message, block=True, timeout=None)
        
        self.handler = handler or default_handler
        mqtt.do_subscribe(topic, self)

        
    def do_handle(self, message:str):
        self.handler(message)


    def has_data(self):
        return not self.queue.empty()

        
    def get(self):
        return self.queue.get(block=True, timeout=None)

        
            
if __name__ == '__main__':
    import sys
    from slowpy.control import control_system as ctrl
    mqtt = ctrl.import_control_module('MQTT').mqtt('localhost')

    def handler(message):
        sys.stdout.write(f'\n{message}\n> ')
    mqtt.subscribe('chat', handler)
        
    while True:
        try:
            line = input('> ')
        except:
            break
        mqtt.publish('chat').set(line)

    mqtt.close()
    
