# Created by Sanshiro Enomoto on 26 October 2023 #


import os, sys, time, json, io, datetime, logging
from collections import namedtuple
from urllib import request, parse
try:
    import pandas as pd
except ImportError:
    pd = None

from .basetypes import DataElement
from .histograms import Histogram, Histogram2d
from .graphs import Graph


class SlowFetch:
    def __init__(self, url):
        """
        Args:
          - url: SlowDash Web server URL
        """
        self.baseurl = url + '/api'
        self.opener = None


    def set_user(self, username, password):
        """If the SlowDash web server is password protected, set the credentials using this.
        Args:
          - username: user name
          - password: password
        """
        self.pwd_mgr = request.HTTPPasswordMgrWithPriorAuth()
        self.pwd_mgr.add_password(None, self.baseurl, username, password, is_authenticated=True)
        self.auth_mgr = request.HTTPBasicAuthHandler(self.pwd_mgr)
        self.opener = request.build_opener(self.auth_mgr)
        
        
    def channels(self, fields=['name','type']):
        """Obtain a list of channels.
        Args:
          - fields: str (e.g., 'name') or list (e.g. ['name','type'])
        Returns:
          - list of field values (e.g., ['ch0', 'ch1']), or
            list of channels where channel is a named-tuple of the fields
        """
        data = json.loads(self._http_get('%s/channels' % self.baseurl).decode())
        table = []
        if type(fields) == str:
            table = [
                record.get(fields, None if fields != 'type' else 'timeseries') for record in data
            ]
        elif type(fields) == list:
            Channel = namedtuple('Channel', fields)
            for record in data:
                f = { field: record.get(field, None if field != 'type' else 'timeseries') for field in fields }
                table.append(Channel(**f))
        return table


    def data(self, channels, start=-3600, stop=0, resample=None, reducer='last', filler=None):
        """Fetch data contents
        Args:
          - channels   List of channels
          - start:     Date-time string, UNIX time, or negative integer for seconds to "stop"
          - stop:      Date-time string, UNIX time, or non-positive integer for seconds to "now"
          - resample:  resampling time-backets intervals, zero for auto, None for no-resampling
          - reducer:   'last' (None), 'mean', or 'median'
          - filler:    'fillna' (None), 'last', or 'linear': ### NOT YET IMPLEMENTED ###
        Returns:
          dict of { channel: (t, x) } where t and x are list of time-series points.
          x can be a list of scalars (time-series), or list of objects (histogram, graph, etc.)
        """
        to, length = self._find_time_range(start, stop)
        if to is None:
            if pd is not None:
                df = pd.DataFrame(columns=['DateTime', 'TimeStamp']+channels)
                return df
            return {}
        
        url = '%s/data/%s?length=%f&to=%f' % (self.baseurl, ','.join(channels), length, to)
        if resample is not None:
            url += '&resample=%s&reducer=%s' % (resample, reducer)
            if filler is not None:
                url += '&filler=%s' % filler
            
        reply = json.loads(self._http_get(url).decode())

        result = {}
        for ch, data in reply.items():
            t0 = data.get('start', 0)
            t = data.get("t", [])
            x = data.get("x", [])
            if not isinstance(t, list):
                t = [t]
            if not isinstance(x, list):
                x = [x]
            if len(t) != len(x) or len(t) == 0:
                print("ERROR: badly formatted data: %s" % ch)
                continue

            result[ch] = (list(), list())
            for k in range(len(t)):
                tk, xk = float(t[k]) + t0, x[k]
                if type(xk) is str:  # JSON value stored as a string
                    try:
                        xk = json.loads(xk)
                    except:
                        pass
                if type(xk) is dict:
                    xk = self._create_object(xk)
                if xk is not None:
                    result[ch][0].append(datetime.datetime.fromtimestamp(tk))
                    result[ch][1].append(xk)
            
        return result

        
    def _create_object(self, data):
        """INTERNAL USE: creates a SlowPy obects (Histogram/Graph/...) from Python dict
        """
        if type(data) is not dict:
            return data
    
        if 'bins' in data:
            return Histogram.from_json(data)
        elif 'ybins' in data:
            return Histogram2d.from_json(data)
        elif 'y' in data:
            return Graph.from_json(data)
        
        return None


    def _find_time_range(self, start, stop):
        """INTERNAL USE: calculates time range in UNIX timestamps
        Args:
          - start:     Date-time string, UNIX time, or negative integer for seconds to "stop"
          - stop:      Date-time string, UNIX time, or non-positive integer for seconds to "now"
        Returns:
          a time-range in UNIX time as a pair of (stop, length)
        """
        if isinstance(stop, (int, float)):
            pass
        elif isinstance(stop, datetime.datetime):
            stop = stop.timestamp()
        else:
            try:
                stop = datetime.datetime.fromisoformat(stop).timestamp()
            except Exception as e:
                logging.error(f'bad stop time: {e}: {stop}')

        if isinstance(start, (int, float)):
            pass
        elif isinstance(start, datetime.datetime):
            start = start.timestamp()
        else:
            try:
                start = datetime.datetime.fromisoformat(start).timestamp()
            except Exception as e:
                logging.error(f'bad start time: {e}: {start}')

        if start < 0:
            length = abs(start)
        else:
            if stop > 0:
                length = abs(stop - start)
            else:
                length = min(time.time()+stop - start, 0)
        if length > 315576000: # ten years
            return None, None
        
        return (stop, length)


    def _http_get(self, url):
        """INTERNAL USE: make a HTTP request and receives a reply
        """
        if self.opener is not None:
            with self.opener.open(url) as reply:
                return reply.read()
        else:
            with request.urlopen(request.Request(url)) as reply:
                return reply.read()
