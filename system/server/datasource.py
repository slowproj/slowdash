#! /usr/bin/env python3
# Created by Sanshiro Enomoto on 20 March 2022 #

import sys, os, glob, math, re, json, enum, datetime, time, logging, traceback
import importlib.machinery
import numpy as np


class Schema:
    tag_field_separator = ':'
    
    def __init__(self, schema=None, tag_values=[]):
        self.init_description = schema
        self.init_tag_values = tag_values
        self.initialize()

        
    def initialize(self):
        self.table = None
        self.tag = None
        self.flags = []
        self.time = None
        self.time_type = None
        self.fields = []
        self.field_types = []
        
        self.default_field = None
        self.tag_values = self.init_tag_values
        self.suffix = ''

        self.channel_table = {}
        self.parse(self.init_description)

            
    def parse(self, schema):
        # syntax:  TABLE [TAG, FLAG, FLAG...] @TIME(TIME_TYPE) = FIELD(OPT), FIELD(OPT), ...
        # all elements are optional
        # quote with " or ' to use special characters
        
        class State(enum.Enum):
            TABLE=1
            TAGFLAG=2
            AFTER_TAGFLAG=3
            TIME=4
            TIME_TYPE=5
            AFTER_TIME=6
            FIELD=7
            FIELD_OPTS=8
            AFTER_FIELD_OPTS=9
        state = State.TABLE
        token = ''
        quote = None
        
        if schema is None:
            return

        for ch in str(schema):
            if ch == "'" or ch == '"':
                if quote is None:
                    quote = ch
                    continue
                elif ch == quote:
                    quote = None
                    continue
            if quote is not None:
                token += ch
                continue
            if ch == ' ':
                continue
            
            if state == State.TABLE:
                if ch == '[':
                    state = State.TAGFLAG
                elif ch == '@':
                    state = State.TIME
                elif ch == '=':
                    state = State.FIELD
                if state == State.TABLE:
                    token += ch
                else:
                    if len(token) > 0:
                        self.table = token
                        token = ""
                    
            elif state == State.TAGFLAG:
                if ch == ',':
                    if len(token) > 0:
                        if self.tag is None:
                            self.tag = token
                        else:
                            self.flags.append(token)
                        token = ''
                elif ch == ']':
                    if len(token) > 0:
                        if self.tag is None:
                            self.tag = token
                        else:
                            self.flags.append(token)
                        token = ''
                    state = State.AFTER_TAGFLAG
                else:
                    token += ch
                    
            elif state == State.AFTER_TAGFLAG:
                if ch == '@':
                    state = State.TIME
                elif ch == '=':
                    state = State.FIELD
                else:
                    token += ch

                if state != State.AFTER_TAGFLAG and len(token) > 0:
                    logging.error('invalid schema: extra token after tags: "%s"' % token)
                    token = ''

            elif state == State.TIME:
                if ch == '=':
                    if len(token) > 0:
                        self.time = token
                        token = ''
                    state = State.FIELD
                elif ch == '(':
                    if len(token) > 0:
                        self.time = token
                        token = ''
                    state = State.TIME_TYPE
                else:
                    token += ch
                    
            elif state == State.TIME_TYPE:
                if ch == ')':
                    if len(token) > 0:
                        self.time_type = token
                        token = ''
                    state = State.AFTER_TIME
                else:
                    token += ch

            elif state == State.AFTER_TIME:
                if ch == '=':
                    state = State.FIELD
                    if len(token) > 0:
                        logging.error('invalid schema: extra token after time: "%s"' % token)
                        token = ''
                else:
                    token += ch

            elif state == State.FIELD:
                if ch == '(':
                    if len(token) > 0:                    
                        self.fields.append(token)
                        token = ''
                    state = State.FIELD_OPTS
                elif ch == ',':
                    if len(token) > 0:
                        self.fields.append(token)
                        self.field_types.append(None)
                        token = ''
                else:
                    token += ch
                    
            elif state == State.FIELD_OPTS:
                if ch == ')':
                    field_type = None
                    if len(token) > 0:
                        for elem in token.split(','):
                            if elem[0:5].lower() == 'type=' and len(elem) > 5:
                                field_type = elem[5:]
                            elif elem.lower() == 'default':
                                self.default_field = self.fields[-1]
                        token = ''
                    self.field_types.append(field_type)
                    state = State.AFTER_FIELD_OPTS
                else:
                    token += ch
                
            elif state == State.AFTER_FIELD_OPTS:
                if ch == ',':
                    state = State.FIELD
                    if len(token) > 0:
                        logging.error('invalid schema: extra field type: "%s"' % token)
                        token = ''
                else:
                    token += ch

        if len(token) > 0:
            if state == State.TABLE:
                self.table = token
            elif state == State.FIELD:
                self.fields.append(token)
                self.field_types.append(None)
            else:
                logging.error('invalid schema: extra token: "%s"' % token)

        if len(self.fields) == 1:
            self.default_field = self.fields[0]

                
    def get_query_times(self, start, stop, time_sep='T'):
        if self.time == None:
            time_from = '%d' % start
            time_to = '%d' % stop
        elif self.time_type == 'unix':
            time_from = '%d' % start
            time_to = '%d' % stop
        else:
            datetime_start = datetime.datetime.fromtimestamp(start)
            datetime_stop = datetime.datetime.fromtimestamp(stop)
            if self.time_type == 'naive':
                pass
            else:
                datetime_start = datetime_start.astimezone(datetime.timezone.utc)
                datetime_stop = datetime_stop.astimezone(datetime.timezone.utc)
                if self.time_type == 'aware':
                    pass
                elif self.time_type == 'unspecifiedutc':
                    datetime_start = datetime_start.replace(tzinfo=None)
                    datetime_stop = datetime_stop.replace(tzinfo=None)
                else:
                    return None, None, None
            time_from = "'%s'" % datetime_start.isoformat(sep=time_sep)
            time_to = "'%s'" % datetime_stop.isoformat(sep=time_sep)

        if self.time is not None:
            time_col = self.time
        else:
            time_col = '%d' % int(time.time())
                
        return time_col, time_from, time_to

        
    def get_query_tagvalues_fields(self, target_channels):
        tag_values, fields = [],  []
        name_mapping = {}
        if self.tag is None:
            # no tag: channel by field only
            for ch in target_channels:
                if ch in self.fields:
                    fields.append(ch)
        else:
            # tag and fields
            for name in target_channels:
                tagfield = name.split(self.tag_field_separator, 1)
                if len(tagfield) == 1:
                    # tag only
                    if self.default_field is None:
                        # no field to read defined
                        continue
                    tag_value, field = tagfield[0], self.default_field
                    channel = '%s%s%s' % (tag_value, self.tag_field_separator, field)
                    name_mapping[channel] = name
                else:
                    # tag and fields
                    tag_value, field = tagfield[0], tagfield[1]
                if tag_value not in tag_values:
                    tag_values.append(tag_value)
                if field not in fields:
                    if field in self.fields:
                        fields.append(field)
                            
        return tag_values, fields, name_mapping

        
    @staticmethod
    def identify_datatype(value):
        if value is None:
            return None
        
        if isinstance(value, float) or isinstance(value, int):
            return 'timeseries'
        
        if isinstance(value, str):
            json_value = value.strip()
            if not (len(json_value) > 2 and json_value[0] == '{' and json_value[-1] == '}'):
                return 'timeseries'
            try:
                json_value = json.loads(json_value)
            except Exception as e:
                return 'timeseries'
        else:
            json_value = value
            
        if 'counts' in json_value:
            if 'xbins' in json_value:
                return 'histogram2d'
            else:
                return 'histogram'
        elif 'y' in json_value:
            return 'graph'
        elif 'table' in json_value:
            return 'table'
        elif 'tree' in json_value:
            return 'tree'
        elif 'mime' in json_value:
            return 'blob'
        else:
            return 'json'


    @staticmethod
    def parse_dburl(url):
        config = {
            'type': None,
            'user': None,
            'password': None,
            'host': None,
            'port': None,
            'db': None
        }
        if url is None or len(url) == 0:
            return config
        
        match = re.findall(r'^[a-zA-Z]+://', url)
        if len(match) > 0:
            config['type'] = match[0][0:-3]
            url = url[len(match[0]):]
        pos = url.find('@')
        if pos > 0:
            auth = url[0:pos]
            url = url[pos+1:]
            pos = auth.find(':')
            if pos > 0:
                config['user'] = auth[0:pos]
                config['password'] = auth[pos+1:]
            else:
                config['user'] = auth
        pos = url.find('/')
        if pos > 0:
            config['db'] = url[pos+1:]
            url = url[0:pos]
        pos = url.find(':')
        if pos > 0:
            config['host'] = url[0:pos]
            config['port'] = url[pos+1:]
        else:
            config['host'] = url
            
        return config


    
            
class DataSource:
    def __init__(self, project_config, datasource_config):
        self.project_config = project_config
        self.config = datasource_config

    # this must be implemented by a child class
    def get_channels(self):
        return []

    
    # this must be implemented by a child class
    def get_timeseries(self, channels, length, to, resampling=None, reducer='last'):
        return {}

    
    # this can be implemented by a child class, if such function is available in the data store
    def get_object(self, channels, length, to):
        return {}

    # this can be implemented by a child class, if such function is available in the data store
    def get_blob(self, channel, params, output):
        mime_type = None
        return mime_type  # fill into output and return the mime_type

    
    # this can be overriden by a child class, if more efficient processing is possible
    def get_dataframe(self, channels, length, to, resampling=None, reducer='last', timezone='local'):
        if resampling is None:
            interval = 0
        else:
            interval = float(resampling)

        timeseries = self.get_timeseries(channels, length, to, interval, reducer)
        if timeseries is None:
            return None

        table = [ ['DateTime', 'TimeStamp'] ]
        table[0].extend(timeseries.keys())
        for name, data in timeseries.items():
            start = data.get('start', 0)
            tk = data.get('t', [])
            xk = data.get('x', [])
            for k in range(len(tk)):
                if len(table) <= k+1:
                    t = int(10*(start+tk[k]))/10.0
                    date_local = datetime.datetime.fromtimestamp(t)
                    date_utc = datetime.datetime.utcfromtimestamp(t)
                    if timezone.upper() == 'LOCAL':
                        date = date_local
                        timediff = abs((date_local - date_utc).total_seconds())
                        tz = '+' if date_local > date_utc else '-'
                        tz = tz + '%02d:%02d' % (int(timediff/3600), int(timediff%3600))
                    else:
                        date = date_utc
                        tz = '+00:00'
                        
                    table.append([ date.strftime('%Y-%m-%dT%H:%M:%S') + tz, '%d' % t ])
                table[k+1].append(str(xk[k]) if xk[k] is not None else 'null')

        return table

    
    # this can be used by a child class
    def resample(self, set_of_timeseries, length, to, interval, reducer):
        if interval is None:
            return set_of_timeseries

        if interval <= 0:
            intervals = []
            for name, data in set_of_timeseries.items():
                if data is None:
                    continue
                t = data.get('t', [])
                if len(t) > 1:
                    intervals.append(np.median(np.diff(t)))
            if len(intervals) > 0:
                interval = np.median(intervals)
            else:
                interval = length / 100
            if interval <= 0:
                interval = 1

        nbins = math.floor(length/interval)
        start = to - nbins * interval
        if length - nbins*interval > 0:
            start = start - interval
            nbins = nbins + 1

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

            x = [ self._reduce(xk, reducer) for xk in buckets ]
            x = np.where(np.isnan(x), None, x).tolist()
                
            result[name] = { 'start': start, 'length': length, 't': t, 'x': x }
            
        return result

    
    def _reduce(self, x, method):
        x = np.array(x)
        x = x[~np.isnan(x)]
        if method != 'count' and len(x) == 0:
            return np.nan
        
        if method == 'first':
            return x.tolist()[0]
        elif method == 'last':
            return x.tolist()[len(x)-1]
        elif method == 'mean':
            return np.mean(x)
        elif method == 'median':
            return np.median(x)
        elif method == 'sum':
            return np.sum(x)
        elif method == 'count':
            return len(x)
        elif method == 'std':
            return np.std(x)
        elif method == 'min':
            return np.min(x)
        elif method == 'max':
            return np.max(x)
        
        return np.nan
    
    

def load(ds_type, project_config, datasource_config):
    moduledir = os.path.abspath(os.path.join(project_config.sys_dir, 'system', 'plugin'))
    for plugin_file in glob.glob(os.path.join(moduledir, 'datasource_*.py')):
        name = os.path.basename(plugin_file)[11:-3]
        if ds_type.lower() == name.lower():
            ds_type = name
            break
    else:
        logging.error('unable to find datasource plugin: %s' % ds_type)
        return None
        
    modulename = 'datasource_%s.py' % ds_type
    filepath = os.path.abspath(os.path.join(moduledir, modulename))
    try:
        module = importlib.machinery.SourceFileLoader(modulename, filepath).load_module()
    except Exception as e:
        logging.error('unable to load datasource module: %s: %s' % (modulename, str(e)))
        logging.error(traceback.format_exc())
        return None
    logging.debug('loaded datasource module "%s"' % modulename)

    datasource = None
    classname = 'DataSource_%s' % ds_type    
    if classname in module.__dict__:
        datasource = module.__dict__[classname](project_config, datasource_config)
        datasource.modulename = modulename
    else:
        logging.error('no entry found in datasource driver: %s' % modulename)
        
    return datasource
