# Created by Sanshiro Enomoto on 26 October 2023 #


import os, sys, time, json, io, datetime, logging
import pandas as pd
from urllib import request, parse
from .dataobject import DataObject


class SlowFetch:
    def __init__(self, url, user=None, passwd=None):
        self.baseurl = url + '/api'
        self.opener = None


    def set_user(self, user, passwd):
        self.pwd_mgr = request.HTTPPasswordMgrWithPriorAuth()
        self.pwd_mgr.add_password(None, self.baseurl, user, passwd, is_authenticated=True)
        self.auth_mgr = request.HTTPBasicAuthHandler(self.pwd_mgr)
        self.opener = request.build_opener(self.auth_mgr)
        
        
    def channels(self):
        data = json.loads(self._http_get('%s/channels' % self.baseurl).decode())
        table = [ [ record['name'], record.get('type', 'timeseries') ] for record in data ]
        return pd.DataFrame(table, columns=['name', 'type'])


    def dataframe(self, channels, start=-3600, stop=0, resample=None, reducer='last', filler=None):
        to, length = self._find_time_range(start, stop)
        if to is None:
            df = pd.DataFrame(columns=['DateTime', 'TimeStamp']+channels)
            return df
        
        url = '%s/dataframe/%s?length=%f&to=%f' % (self.baseurl, ','.join(channels), length, to)
        if resample is not None:
            url += '&resample=%s&reducer=%s' % (resample, reducer)
            if filler is not None:
                url += 'filler=%s' % filler
            
        return pd.read_csv(io.StringIO(self._http_get(url).decode()), parse_dates=['DateTime'])
    
        
    def lastobj(self, channels, start=-3600, stop=None):
        to, length = self._find_time_range(start, stop)
        if not (to > 0):
            return None
        
        url = '%s/data/%s?length=%f&to=%f&reducer=last' % (self.baseurl, ','.join(channels), length, to)            
        data = json.loads(self._http_get(url).decode())

        result = {}
        for ch in data:
            x = data[ch].get("x")
            if isinstance(x, list):
                if len(x) < 1:
                    continue
                x = x[-1]
            if isinstance(x, str):  # JSON value stored as a string
                try:
                    x = json.loads(x)
                except:
                    pass
            result[ch] = DataObject.from_json(ch, x)
            
        return result
    
        
    def _find_time_range(self, start, stop):
        now = time.time()

        if isinstance(stop, (int, float)):
            if stop <= 0:
                stop = now + stop
        elif isinstance(stop, datetime.datetime):
            stop = stop.timestamp()
        else:
            stop = datetime.datetime.fromisoformat(stop).timestamp()

        if isinstance(start, (int, float)):
            if start <= 0:
                start = stop + start
        elif isinstance(start, datetime.datetime):
            start = start.timestamp()
        else:
            start = datetime.datetime.fromisoformat(start).timestamp()

        if stop < start:
            length = start - stop
            stop = start
        elif stop > start:
            length = stop - start
        else:
            length = 3600
            
        if length > 315576000: # ten years
            return None, None
        
        return (stop, length)


    def _http_get(self, url):
        if self.opener is not None:
            with self.opener.open(url) as reply:
                return reply.read()
        else:
            with request.urlopen(request.Request(url)) as reply:
                return reply.read()
