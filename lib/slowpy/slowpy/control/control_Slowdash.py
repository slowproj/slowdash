# Created by Sanshiro Enomoto on 4 September 2024 #


import slowpy.control as spc


class SlowdashNode(spc.ControlNode):
    def __init__(self, http_node):
        self.http = http_node
        
    @classmethod
    def _node_creator_method(cls):
        def slowdash(self):
            if self.__class__.__name__ != 'HttpNode':
                raise spc.ControlException('SlowdashNode can be inserted only to HttpNode')
            return SlowdashNode(self)
        return slowdash

    
    ### Child Nodes ###
    def ping(self):
        return self.http.path('/api/ping').json().readonly()
    
    def config(self):
        return self.http.path('/api/config').json().readonly()
    
    def channels(self):
        return self.http.path('/api/channels').json().readonly()
    
    def data(self, channels, length=3600, **options):
        if type(channels) is list:
            url = f"/api/data/{','.join(channels)}"
        else:
            url = f"/api/data/{channels}"
        opts = { 'length': length }
        opts.update(options)
        return self.http.path(url,**opts).json().readonly()

    def config_file(self, name, **options):
        opts = { 'overwrite': 'yes' }
        opts.update(options)
        return self.http.path(f'/api/config/file/{name}', **opts)
