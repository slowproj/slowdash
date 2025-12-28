# Created by Sanshiro Enomoto on 20 March 2022 #

import os, time, math, json, statistics, logging

import slowlette
from sd_component import ComponentPlugin, PluginComponent

from sd_dataschema import Schema
import sd_blobstorage


class DataSource(ComponentPlugin):
    """Base class for DataSource plugin
    """
    
    def __init__(self, app, project, params):
        super().__init__(app, project, params)

        self.blob_storage = None
        if 'blob_storage' in params:
            blob_params = params.get('blob_storage')
            if blob_params.get('type', '') == 'file':
                self.blob_storage = sd_blobstorage.BlobStorage_File(app, project, blob_params)
        
        
    @slowlette.on_event('startup')
    async def api_initialize(self):
        return await self.aio_initialize()

    
    @slowlette.on_event('shutdown')
    async def api_finalize(self):
        return await self.aio_finalize()

    
    @slowlette.get('/api/channels')
    async def api_get_channels(self):
        return await self.aio_get_channels()

    
    @slowlette.get('/api/data/{channels}')
    async def api_get_data(self, channels:str, opts:dict):
        try:
            channels = channels.split(',')
            length = float(opts.get('length', 3600))
            to = float(opts.get('to', 0))
            resample = float(opts.get('resample', -1))
            reducer = opts.get('reducer', 'last')
            envelope = int(opts.get('envelope', 0))
        except Exception as e:
            logging.error('Bad data URL: %s: %s' % (str(opts), str(e)))
            return slowlette.Response(400)
        
        if to <= 0:
            to = to + time.time()
        if resample < 0:
            resample = None
                                
        result = {}
        result_ts = await self.aio_get_timeseries(channels, length, to, resample, reducer, envelope)
        result_obj = await self.aio_get_object(channels, length, to)
        if result_ts is not None:
            result.update(result_ts)
        if result_obj is not None:
            result.update(result_obj)

        return result

    
    @slowlette.get('/api/blob/{channel}')
    async def api_get_blob(self, channel:str, id:str):
        mime_type, content = await self.aio_get_blob(channel, id)
        
        if content is None:
            if self.blob_storage is not None:
                if channel in [entry['name'] for entry in self.get_channels()]:
                    mime_type, content = await self.blob_storage.get_blob(id)
                
        return slowlette.Response(content_type=mime_type, content=content)

    
    async def aio_initialize(self):
        return self.initialize()

    
    async def aio_finalize(self):
        return self.finalize()
        
                    
    async def aio_get_channels(self):
        """[implement in child class] returns a list of channels (async version)
        """
        return self.get_channels()

    
    async def aio_get_timeseries(self, channels, length, to, resampling=None, reducer='last', envelope=0):
        """[implement in child class] returns a time-series data (async version)
        """
        return self.get_timeseries(channels, length, to, resampling, reducer, envelope)

    
    async def aio_get_object(self, channels, length, to):
        """[implement in child class] returns a single-point data object (async version)
        """
        return self.get_object(channels, length, to)

    
    async def aio_get_blob(self, channel:str, blob_id:str):
        """[implement in child class] returns a tuple of content_type (str) and blob (bytes)  (async version)
        """
        return self.get_blob(channel, blob_id)


    def initialize(self):
        pass

    
    def finalize(self):
        pass
        
                    
    def get_channels(self):
        """[implement in child class] returns a list of channels
        """
        return []

    
    def get_timeseries(self, channels, length, to, resampling=None, reducer='last', envelope=0):
        """[implement in child class] returns a time-series data
        """
        return {}

    
    def get_object(self, channels, length, to):
        """[implement in child class] returns a single-point data object
        """
        return {}

    
    def get_blob(self, channel:str, blob_id:str):
        """[override in child class as needed] returns a tuple of content_type (str) and blob (bytes)
        """
        return None, None
            

    @classmethod
    def resample(cls, set_of_timeseries, length, to, interval, reducer, envelope):
        """performs resampling (can be used in child class)
        Args:
          - set_of_timeseries: { name: timeseries } dict of input timeseries objects
          - length, to: defines the time frame (start/stop)
          - interval: time-bucket interval in sec
          - reducer: name of the reducer applied, defined in DataSource.reduce()
          - envelope: 0: no envelope, 1: min/max envelope
        Returns:
          - set of aligned timeseries, in a { name: timeseries } dict
        """
        
        if interval is None:
            return set_of_timeseries

        if interval <= 0:
            intervals = []
            for name, data in set_of_timeseries.items():
                if data is None:
                    continue
                t = data.get('t', [])
                if len(t) > 1:
                    dt = [ t[k+1]-t[k] for k in range(len(t)-1) ]
                    intervals.append(statistics.median(dt))
            if len(intervals) > 0:
                interval = statistics.median(intervals)
            else:
                interval = length / 100
            if interval <= 0:
                interval = 1

        nbins = math.floor(length/interval)
        start = to - nbins * interval
        if length - nbins*interval > 0:
            start = start - interval
            nbins = nbins + 1

        def _reduce_buckets(buckets, reducer):
            x = [ cls.reduce(bk, reducer) for bk in buckets ]
            x = [ None if math.isnan(xk) else xk for xk in x ]
            return x
                
        result = {}
        for name, data in set_of_timeseries.items():
            if data is None:
                continue
            t0 = data.get('start', 0) - start
            t_in = data.get('t')
            x_in = data.get('x')
            
            t, buckets = [], []
            for bin in range(nbins):
                t.append(float(interval) * (bin + 0.5))
                buckets.append([])

            for k in range(len(x_in)):
                bin = math.floor((t0 + t_in[k]) / interval)
                if bin < 0 or bin >= nbins:
                    continue
                buckets[bin].append(x_in[k])

            x = _reduce_buckets(buckets, reducer)
            result[name] = { 'start': start, 'length': length, 't': t, 'x': x }

            if envelope >= 1:
                if reducer in ['first', 'last', 'mean', 'median']:
                    result[name]['x_min'] = _reduce_buckets(buckets, 'min')
                    result[name]['x_max'] = _reduce_buckets(buckets, 'max')
            if envelope >= 2:
                if reducer != 'count':
                    result[name]['x_count'] = _reduce_buckets(buckets, 'count')
                if reducer == 'mean':
                    result[name]['x_err'] = _reduce_buckets(buckets, 'sem')
            
        return result


    @classmethod
    def reduce(cls, x, method):
        """calculate a single scalar number out of the input list of values
        Args:
          - x: list of scalar values
          - method: string name of the reducing method:
            - 'first', 'last', 'mean', 'median'
            - 'min', 'max'
            - 'sum', 'count'
            - 'stdev' (or equivalently, 'sd', 'std', 'rms', 'sigma')
            - 'sem' (or equivalently, 'err'): standard error of mean (= stdev/sqrt(count))
        Returns:
          - the calculated scalar value
        """

        xx = [ xk for xk in x if not math.isnan(xk) ]

        if method == 'count':
            return len(xx)
        
        if len(xx) < 1:
            return math.nan
        
        if method == 'first':
            return xx[0]
        elif method == 'last':
            return xx[len(xx)-1]
        elif method == 'mean':
            return statistics.mean(xx)
        elif method == 'median':
            return statistics.median(xx)
        elif method == 'sum':
            return sum(xx)
        elif method == 'min':
            return min(xx)
        elif method == 'max':
            return max(xx)
        
        if len(xx) < 2:
            return math.nan
        
        if method in ['sd','std','stdev','rms','sigma']:
            return statistics.stdev(xx)
        elif method in ['sem','err']:
            return statistics.stdev(xx) / math.sqrt(len(xx))
        
        return math.nan

    
    @classmethod
    def decode_if_json(cls, value):
        if type(value) is not str or len(value) < 2:
            return value

        # quickly pre-check whether the value starts with '{' or '[' after skipping white-spaces
        n, k = len(value), 0
        while k < n and value[k] in ('\t', '\n', '\r', ' '):
            k += 1
        if k >= n or value[k] not in ('{', '['):
            return value

        try:
            obj = json.loads(value)
        except:
            return value

        return obj
    
        

class DataSourceComponent(PluginComponent):
    def __init__(self, app, project):
        super().__init__('data_source', app, project)
        

    def build(self, plugin_config):
        for node in plugin_config:
            url = node.get('url', None)
            if url is None:
                continue
            if 'parameters' not in node:
                node['parameters'] = {}
            node['parameters']['url'] = url
            ds_type = Schema.parse_dburl(url).get('type', None)
            if ds_type is not None:
                node['type'] = node.get('type', ds_type)

        return super().build(plugin_config)
