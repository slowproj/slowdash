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

        self.subscribers: dict[str,list[SubscriberNode]] = {}

        try:
            import paho.mqtt.client as mqtt
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        except Exception as e:
            logging.error(f'MQTT: {e}')
            self.client = None
            return

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

        
    def publisher(self, topic):
        return PublisherNode(self, topic)


    def subscriber(self, topic, handler=None, timeout=None):
        return SubscriberNode(self, topic, handler, timeout=timeout)


    def do_subscribe(self, topic_filter:str, subscriber_node):
        if self.client is None:
            return
        
        def mqtt_callback(client, userdata, msg):
            topic, message = str(msg.topic), msg.payload
            logger.debug(f'MQTT message: {topic}: {message.decode()}')
            for subscriber in self.subscribers.get(topic_filter, []):
                subscriber.do_handle_message(msg)

        if topic_filter not in self.subscribers:
            self.subscribers[topic_filter] = []
            self.client.message_callback_add(topic_filter, mqtt_callback)
            self.client.subscribe(topic_filter)

        self.subscribers[topic_filter].append(subscriber_node)

        
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

    
    
class PublisherNode(ControlNode):
    def __init__(self, mqtt, topic):
        self.mqtt = mqtt
        self.topic = topic

        
    def set(self, value):
        if self.mqtt.client is None:
            return None

        self.mqtt.client.publish(self.topic, value)
        

    ## child nodes ##
    # nats.publisher(subject).json()
    def json(self, headers=None):
        return PublisherJsonNode(self, headers)


    
class SubscriberNode(ControlNode):
    def __init__(self, mqtt:MQTTNode, topic_filter:str, handler=None, timeout=None):
        """
        - If handler is not None, it is called on receiving a message.
        - Otherwise, the received messages are queued, which can be retrieved by has_data()/get()
        """
        self.timeout = timeout
                
        self.queue = queue.Queue(maxsize=1024)
        
        def default_handler(message):
            self.queue.put(message, block=True, timeout=None)
        self.handler = handler or default_handler

        mqtt.do_subscribe(topic_filter, self)

        
    def has_data(self):
        return not self.queue.empty()

        
    def get(self):
        try:
            if self.timeout is None:
                return self.queue.get(block=True)
            elif self.timeout <= 0:
                return self.queue.get(block=False)
            else:
                return self.queue.get(timeout=self.timeout)
        except queue.Empty:
            return None
    

    def do_handle_message(self, message):
        return self.handler(message)

        
    ## child nodes ##
    # nats.subscriber(subject).json()
    def json(self):
        return SubscriberJsonNode(self)
        

    
class PublisherJsonNode(ControlNode):
    def __init__(self, publisher_node, headers = None):
        self.publisher_node = publisher_node
        self.headers = dict(headers or {})
        

    def set(self, value):
        try:
            doc = json.dumps(value)
        except Exception as e:
            logger.warning(f'MQTT: publisher(): unable to convert to JSON: {e}')
            return None
        
        return self.publisher_node.set(doc)



class SubscriberJsonNode(ControlNode):
    def __init__(self, subscriber_node):
        self.subscriber_node = subscriber_node
        

    def get(self):
        message = self.subscriber_node.get()
        if message is None:
            return None, None

        headers = {
            'topic': message.topic,
            'message_id': message.mid,
        }
        body = message.payload
        if type(body) is bytes:
            try:
                body = body.decode()
            except:
                body = str(body)
            try:
                doc = json.loads(body)
            except:
                doc = body
                
        return (headers, doc)
        
