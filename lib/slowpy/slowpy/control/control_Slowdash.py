
import slowpy.control as slc


class SlowdashNode(slc.ControlNode):
    def __init__(self, http_node):
        self.http = http_node
        
    def __del__(self):
        pass

    @classmethod
    def _node_creator_method(cls):
        def slowdash(self):
            return SlowdashNode(self)
        return slowdash

    
    def set(self, value):
        return self.http.do_post_request(path='/api', content=value)

    def get(self):
        return self.http.do_get_request(path='/api')


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
