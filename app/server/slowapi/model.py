# Created by Sanshiro Enomoto on 10 January 2025 #


import json, logging


class JSON:
    """Custom type for SlowAPI to recognize that the request-body is a JSON string
    Note:
      - If a request-handler parameter is of this type, SlowAPI interprets the body as JSON.
        - Example:
          | @SlowAPI.post('/doc')
          | def process_doc(doc: JsonDocument):
          |   param1 = doc.get('param1', 0)
      - If the parsing fails, it returns response 400 (Bad Request) and the handler will not be called.
      - If the content data is a dict or list, JSON object can be used as dict or list for common methods,
      - Or use the "value()" method to get the native Python type object.
    """
    
    def __init__(self, body):
        try:
            if type(body) is bytes:
                self.data = json.loads(body.decode())
            else:
                self.data = body
        except Exception as e:
            logging.error('SlowAPI: JSON decoding error: %s' % str(e))
            self.data = None

            
    def value(self):
        return self.data
            

    def __iter__(self):
        if type(self.data) is dict:
            for k, v in self.data.items():
                yield k, v
        elif type(self.data) is list:
            for v in self.data:
                yield v

                
    def __str__(self):
        return str(self.data)

    def __repr__(self):
        return repr(self.data)

    def __len__(self):
        return len(self.data)

    def __getitem__(self, index):
        return self.data[index]

    def __setitem__(self, index, value):
        self.data[index] = value

    def __delitem__(self, index):
        del self.data[index]

    def __contains__(self, item):
        return item in self.data

    def get(self, key, default_value=None):
        # no type check on purpose: letting the error messages (and stack trace) displayed
        return self.data.get(key, default_value)
    
    def keys(self):
        # no type check on purpose
        return self.data.keys()

    def values(self):
        # no type check on purpose
        return self.data.values()

    def items(self):
        # no type check on purpose
        return self.data.items()



class DictJSON(JSON):
    """same as JSON, but the content must be a valid dict
    """
    def __init__(self, body:bytes):
        super().__init__(body)
        if type(self.data) is not dict:
            self.data = None
