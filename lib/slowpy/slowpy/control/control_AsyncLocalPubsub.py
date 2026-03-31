# Created by Sanshiro Enomoto on 29 March 2026 #

import asyncio
import logging


class LocalPubsubNode:
    def __init__(self):
        self.subscribers = {}    # TopicPattern -> set[asyncio.Queue]

    def aio_open():
        pass

    def aio_close():
        pass

    def publisher(self, topic, **kwargs):
        return LocalPublisherNode(self, topic)

    def subscriber(self, topic_filter, timeout=None, **kwargs):
        return LocalSubscriberNode(self, topic_filter, timeout=timeout)

    @classmethod
    def _node_creator_method(cls):
        def async_localpubsub(self):
            return LocalPubsubNode()
        return async_localpubsub


    def _subscribe(self, topic_filter:str, queue):
        pattern = TopicPattern(topic_filter)
        if pattern not in self.subscribers:
            self.subscribers[pattern] = set()
        self.subscribers[pattern].add(queue)

    
    async def _publish(self, topic:str, data):
        for pattern, queues in self.subscribers.items():
            if pattern.match(topic):
                for queue in queues:
                    await queue.put(data)

        
        
class LocalPublisherNode:
    def __init__(self, mq_node, topic):
        self.mq_node = mq_node
        self.topic = topic

        
    async def aio_set(self, value):
        body, headers = (None, {})
        if type(value) is tuple:
            if len(value) == 1:
                (body,) = value
            elif len(value) == 2:
                headers, body = value
        else:
            body = value

        if headers is None:
            headers = {}
        headers['topic'] = self.topic
        doc = {
            'headers': headers,
            'data': body
        }
            
        await self.mq_node._publish(self.topic, doc)

        
    ## child nodes ##
    # localmq.publisher(subject).json()
    def json(self, headers=None):
        return LocalPublisherJsonNode(self, headers)


    
class LocalSubscriberNode:
    def __init__(self, mq_node, topic_filter:str, timeout=None):
        self.mq_node = mq_node
        self.topic_filter = topic_filter
        self.timeout = timeout

        self.queue = asyncio.Queue()
        self.mq_node._subscribe(self.topic_filter, self.queue)

        
    async def aio_has_data(self):
        return not self.queue.empty()

        
    async def aio_get(self):
        try:
            if self.timeout is None:
                return await self.queue.get()
            elif self.timeout <= 0:
                return self.queue.get_nowait()
            else:
                return await asyncio.wait_for(self.queue.get(), timeout=self.timeout)
        except (asyncio.TimeoutError, asyncio.QueueEmpty):
            return None

        
    ## child nodes ##
    # localmq.subscriber(subject).json()
    def json(self):
        return LocalSubscriberJsonNode(self)
        

    
class LocalPublisherJsonNode:
    def __init__(self, publisher_node, headers):
        self.headers_dict = headers
        self.publisher_node = publisher_node

        
    async def aio_set(self, value):
        return await self.publisher_node.aio_set((self.headers_dict, value))

    
    ## (virtual) child nodes ##
    def headers(self, headers):
        self.headers_dict = dict(headers)
        return self

    

class LocalSubscriberJsonNode:
    def __init__(self, subscriber_node):
        self.subscriber_node = subscriber_node

        
    async def aio_get(self):
        msg = await self.subscriber_node.aio_get()
        if msg is None:
            return None, None
        else:
            return msg.get('headers', {}), msg.get('data', None)



class TopicPattern:
    def __init__(self, pattern):
        self.pattern = pattern
        try:
            self.validate()
        except Exception as e:
            logging.error(f'AsyncLocalPubsub: Invalid topic pattern: {pattern}: {e}')
            self.pattern = None
            
        
    def validate(self):
        """
        NATS-like topic wildcard pattern
        Rules:
          - tokens are separated by '.'
          - '*' matches exactly one token
          - '>' matches zero or more trailing tokens
          - '>' must appear only as the last token
          - no partial-token wildcard is allowed
        Examples:
          - topic_match("foo.*.baz", "foo.bar.baz") == True
          - topic_match("foo.>", "foo") == True
          - topic_match("foo.>", "foo.bar.baz") == True
          - topic_match("foo.*", "foo") == False
        """
        
        tokens = self.pattern.split(".") if self.pattern else []
        for i, token in enumerate(tokens):
            if token == ">":
                if i != len(tokens) - 1:
                    raise ValueError("Invalid topic pattern: '>' must be the last token")
            elif ("*" in token) or (">" in token):
                if token != "*":
                    raise ValueError("Invalid topic  pattern: wildcards must occupy an entire token")

        
    def match(self, topic:str)->bool:
        if self.pattern is None:
            return False
        
        pattern_tokens = self.pattern.split(".") if self.pattern else []
        topic_tokens = topic.split(".") if topic else []

        k_pattern = 0  # index for pattern
        k_topic = 0  # index for topic

        while k_pattern < len(pattern_tokens):
            ptoken = pattern_tokens[k_pattern]

            if ptoken == ">":
                # Matches the rest, including zero tokens
                return True

            if k_topic >= len(topic_tokens):
                # Topic ended before pattern did
                return False

            if ptoken == "*":
                k_pattern += 1
                k_topic += 1
                continue

            if ptoken != topic_tokens[k_topic]:
                return False

            k_pattern += 1
            k_topic += 1

        # Pattern consumed; topic must also be fully consumed
        return k_topic == len(topic_tokens)
        
