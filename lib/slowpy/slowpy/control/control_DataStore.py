# Created by Sanshiro Enomoto on 3 October 2024 #


import slowpy.control as spc
from slowpy.store import create_datastore_from_url


class DataStoreNode(spc.ControlNode):
    def __init__(self, url, *args, **kwargs):
        self.store = create_datastore_from_url(url, *args, **kwargs)
        
    ## child nodes ##
    # data_store().tag(tag_name)
    def tag(self, tag_name, appending=True):
        return DataStoreTagNode(self.store, tag_name, appending)
    
    @classmethod
    def _node_creator_method(cls):
        def data_store(self, url, *arg, **kwargs):
            return DataStoreNode(url, *arg, **kwargs)
        return data_store

    
    
class DataStoreTagNode(spc.ControlVariableNode):
    def __init__(self, store, tag_name, appending):
        self.store = store
        self.tag_name = tag_name
        self.appending = appending
            
    def set(self, value):
        if self.appending:
            self.store.append(value, tag=self.tag_name)
        else:
            self.store.update(value, tag=self.tag_name)
            
    ## child nodes ##
    # data_store().tag(tag_name).time(ts)
    def time(self, tag_name, timestamp):
        return DataStoreTagTimeNode(self, timestamp)

    

class DataStoreTagTimeNode(spc.ControlVariableNode):
    def __init__(self, tag_node, timestamp):
        self.tag_node = tag_node
        self.timestamp = timestamp
            
    def set(self, value):
        if self.tag_node.appending:
            self.tag_node.store.append(value, tag=self.tag_name, timetamp=self.timestamp)
        else:
            self.tag_node.store.update(value, tag=self.tag_name, timestamp=self.timestamp)
