
import slowpy.control as slc


class SlowdashNode(slc.ControlNode):
    def __init__(self, http_node):
        self.http = http_node
        
    def __del__(self):
        pass

    @classmethod
    def _node_creator_method(cls):
        def slowdash(self):
            if self.__class__.__name__ != 'HttpNode':
                raise slc.ControlException('SlowdashNode can be inserted only to HttpNode')
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
        opts = { 'length': length }
        opts.update(options)
        return self.http.path(f'/api/data/{channels}',**opts).json().readonly()

    def config_file(self, name, **options):
        opts = { 'overwrite': 'yes' }
        opts.update(options)
        return self.http.path(f'/api/config/file/{name}', **opts)
