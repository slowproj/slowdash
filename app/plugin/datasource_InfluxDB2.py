# Created by Sanshiro Enomoto on 26 May 2022 #


import sys, os, time, datetime, logging, traceback
from sd_dataschema import Schema
from sd_datasource import DataSource

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS



class DataSource_InfluxDB2(DataSource):
    def __init__(self, app, project, params):
        super().__init__(app, project, params)
        self.client = None
        self.channels_scanned = False

        dburl = Schema.parse_dburl(params.get('url', ''))
        self.protocol = params.get('protocol', 'http')
        self.host = params.get('host', dburl.get('host', 'localhost'))
        self.port = params.get('port', dburl.get('port', '8086'))
        self.org = params.get('organization', dburl.get('user', None))
        self.token = params.get('token', dburl.get('password', None))
        self.bucket = params.get('bucket', dburl.get('db', None))

        if self.org is None:
            logging.error('"organization" is not specified')
            return
        if self.token is None:
            logging.error('"token" not provided')
            return
        if self.bucket is None:
            logging.error('"bucket" is not specified')
            return
            
        def load_schema(params, entrytype):
            schema_list = []
            entry_list = params.get(entrytype, [])
            for entry in entry_list if type(entry_list) is list else [ entry_list ]:
                measurement = entry.get('measurement', None)
                schema_conf = entry.get('schema', None)
                if measurement is None and schema_conf is None:
                    logging.error('InfluxDB2: measurement not specified')
                    continue
                if schema_conf is None:
                    schema_conf = measurement
                tag_value_list = entry.get('tags', {}).get('list', [])
                schema = Schema(schema_conf, tag_value_list)
                schema.tag_scan_date = entry.get('tags', {}).get('scan_date', None)
                schema.tag_scan_length = entry.get('tags', {}).get('scan_length', None)
                schema.is_for_objts = (entrytype == 'object_time_series')
                schema.suffix = entry.get('suffix', '')
                schema_list.append(schema)
            return schema_list
        
        self.ts_schemata = load_schema(params, 'time_series')
        self.objts_schemata = load_schema(params, 'object_time_series')

        # "measurement" in URL
        bucket_and_meas = self.bucket.split('/')
        if len(bucket_and_meas) > 1:
            self.bucket, meas = bucket_and_meas
            schema = Schema(meas)
            schema.is_for_objts = False
            self.ts_schemata.append(schema)
            
        self.scan_channels()


    def scan_channels(self):
        if self.channels_scanned:
            return
        self.channels_scanned = True
        
        if self.client is None:
            url = '%s://%s:%s' % (self.protocol, self.host, self.port)
            test_query = '''
                from(bucket:"%s")
                |> range(start: -1s)
            ''' % (self.bucket)
            for i in range(12):
                try:
                    self.client = InfluxDBClient(url=url, org=self.org, token=self.token)
                    self.api = self.client.query_api()
                    self.api.query(test_query, org=self.org)
                    break
                except Exception as e:
                    logging.info(f'Unable to connect to InfluxDB2: {e}')
                    logging.info(f'retrying in 5 sec... ({i+1}/12)')
                    time.sleep(5)
            else:
                logging.error('Unable to connect to InfluxDB2 "%s"' % url)
                logging.error(traceback.format_exc())
                self.client = None
                return

        for schema in self.ts_schemata + self.objts_schemata:
            schema.initialize()
            if schema.table is None:
                logging.error('InfluxDB2: measurement not specified')
                continue

            # time range to scan for tag values
            if schema.tag_scan_date is None:
                tag_scan_stop = 0
            elif type(schema.tag_scan_date) is datetime.datetime:
                tag_scan_stop = schema.tag_scan_date.timestamp()
            elif type(schema.tag_scan_date) is datetime.date:
                tag_scan_stop = datetime.datetime.combine(schema.tag_scan_date, datetime.time(0,0,0)).timestamp()
            else:
                try:
                    tag_scan_stop = float(schema.tag_scan_date)
                except:
                    try:
                        tag_scan_stop = datetime.datetime.fromisoformat(schema.tag_scan_date).timestamp()
                    except Exception as e:
                        logging.error(e)
                        tag_scan_stop = 0
            if tag_scan_stop <= 0:
                tag_scan_stop += time.time()
                
            if schema.tag_scan_length is None:
                tag_scan_start = tag_scan_stop - 864000
            else:
                units = { 's': 1, 'm': 60, 'h': 3600, 'd': 86400, 'w': 7*86400, 'y': 365.25*86400 }
                if schema.tag_scan_length[-1:] in units:
                    length = schema.tag_scan_length[:-1]
                    factor = units[schema.tag_scan_length[-1:]]
                else:
                    length = schema.tag_scan_length
                    factor = 1
                try:
                    tag_scan_start = tag_scan_stop - float(length) * factor
                except:
                    logging.error(f'Invalid tag_scan_length: {schema.tag_scan_length}')
                    tag_scan_start = tag_scan_stop - 864000
                
            # no "tag" and "fields" specified -> find a tag in data schema
            if schema.tag is None and len(schema.fields) < 1:
                query = '''
                    import "influxdata/influxdb/schema"
                    schema.measurementTagKeys(bucket: "%s", measurement: "%s", start: %.0f, stop: %.0f)
                ''' % (self.bucket, schema.table, tag_scan_start, tag_scan_stop)
                try:
                    table = self.api.query(query, org=self.org)[0]
                except Exception as e:
                    logging.error(f'Query: {query}')
                    logging.error(e)
                    table = []
                for record in table:
                    tag = record.get_value()
                    if len(tag) > 0 and tag[0] != '_':
                        schema.tag = tag
                        break
                
            # "tag" specified but no tag values specified -> find tag values in data table
            if schema.tag is not None and len(schema.tag_values) == 0:
                query = '''
                    import "influxdata/influxdb/schema"
                    schema.measurementTagValues(bucket: "%s", measurement: "%s", tag: "%s", start: %.0f, stop: %.0f)
                ''' % (self.bucket, schema.table, schema.tag, tag_scan_start, tag_scan_stop)
                try:
                    table = self.api.query(query, org=self.org)[0]
                except Exception as e:
                    logging.error(f'Query: {query}')
                    logging.error(e)
                    table = []
                schema.tag_values = [record.get_value() for record in table]

            # no "fields" specified -> find fields in data schema
            if len(schema.fields) == 0:
                query = '''
                    import "influxdata/influxdb/schema"
                    schema.measurementFieldKeys(bucket: "%s", measurement: "%s", start: %.0f, stop: %.0f)
                ''' % (self.bucket, schema.table, tag_scan_start, tag_scan_stop)
                try:
                    table = self.api.query(query, org=self.org)[0]
                except Exception as e:
                    logging.error(f'Query: {query}')
                    logging.error(e)
                    table = []
                schema.fields = [record.get_value() for record in table]
                schema.field_types = [None] * len(schema.fields)
                if len(schema.fields) == 1:
                    schema.default_field = schema.fields[0]

            if schema.tag is None:
                for k in range(len(schema.fields)):
                    schema.add_channel(schema.fields[k], schema.field_types[k])
            else:
                for tag_value in schema.tag_values:
                    for k in range(len(schema.fields)):
                        field = schema.fields[k]
                        if field == schema.default_field:
                            ch = tag_value
                        else:
                            ch = '%s%s%s' % (tag_value, Schema.tag_field_separator, field)
                        schema.add_channel(ch, schema.field_types[k])

            if schema.is_for_objts:
                for ch in schema.channel_table:
                    if schema.channel_table[ch].get('type', None) is not None:
                        continue
                    for length in [ 3600, 86400, 365*86400 ]:
                        result = self.execute_query(
                            schema, [ch], length, time.time(), resampling=None, reducer=None, lastonly=True
                        )
                        if result.get(ch, None) is not None:
                            value = result[ch].get('x', {})
                            if type(value) is list and len(value) > 0:
                                value = value[0]
                            schema.add_channel(ch, Schema.identify_datatype(value)) # update fieldtype
                            break
                
        
    def get_channels(self):
        self.channels_scanned = False  # forced scan; efficient for existing channels
        self.scan_channels()
            
        channels = []
        for schema in self.ts_schemata + self.objts_schemata:
            for ch in schema.channel_table.values():
                ch['name'] = ch['name'] + schema.suffix
                channels.append(ch)
                
        return channels
    
    
    def get_timeseries(self, channels, length, to, resampling=None, reducer='last', envelope=0):
        if not self.channels_scanned:
            self.scan_channels()
        if self.client is None:
            return None

        result = {}
        for schema in self.ts_schemata:
            result.update(self.execute_query(
                schema, channels, length, to, resampling=resampling, reducer=reducer, lastonly=False
            ))
            
        if resampling is None:
            return result
        if resampling > 0 and reducer in ['first', 'last', 'min', 'max', 'mean', 'median', 'sum', 'count', 'std']:
            # resampling applied in DB
            return result
        
        return self.resample(result, length, to, resampling, reducer, envelope)
        

    def get_object(self, channels, length, to):
        if not self.channels_scanned:
            self.scan_channels()
        if self.client is None:
            return None

        result = {}
        for schema in self.objts_schemata:
            if schema.tag is None:
                result.update(self.execute_query(
                    schema, channels, length, to, resampling=None, reducer=None, lastonly=True
                ))
            else:
                # to make use of "|> last()"
                for ch in channels:  
                    result.update(self.execute_query(
                        schema, [ch], length, to, resampling=None, reducer=None, lastonly=True
                    ))
            # retry if the value is null?

        return result

            
    def execute_query(self, schema, channels, length, to, resampling=None, reducer=None, lastonly=False):
        result = {}
        stop = int(to)
        start = int(stop - float(length))
        
        target_channels = []
        for name in channels:
            if not name.replace('.', '').replace('_', '').replace('-', '').replace(':', '').isalnum():
                logging.error('bad channel name: %s' % name)
            else:
                key = name[0:len(name)-len(schema.suffix)]
                if key in schema.channel_table:
                    target_channels.append(key)
        if len(target_channels) == 0:
            return result

        tag_values, fields, name_mapping = schema.get_query_tagvalues_fields(target_channels)
        if len(fields) < 1:
            return result
        tag_value_regex = '^(%s)$' % '|'.join(tag_values).replace('.','\\.')
        fields_regex = '^(%s)$' % '|'.join(fields).replace('.','\\.')
        
        query_lines = []
        query_lines.append('from(bucket: "%s")' % self.bucket)
        query_lines.append('|> range(start: %d, stop: %d)' % (start, stop))
        query_lines.append('|> filter(fn: (r) => r._measurement == "%s")' % schema.table)
        if len(tag_values) > 0:
            query_lines.append('|> filter(fn: (r) => r.%s =~ /%s/)' % (schema.tag, tag_value_regex))
        query_lines.append('|> filter(fn: (r) => r._field =~ /%s/)' % fields_regex)
        if resampling is not None and resampling > 0:
            if reducer == 'std':
                reducer = 'stddev'
            if reducer in ['first', 'last', 'min', 'max', 'mean', 'median', 'sum', 'count', 'stddev']:
                query_lines.append('|> aggregateWindow(every: %dms, fn: %s)' % (int(1000*resampling), reducer))
                resampling = None
        if (len(target_channels) == 1 or schema.tag is None) and lastonly:
            query_lines.append('|> last()')
        query = '\n'.join(query_lines)

        #print(query)
        tables = self.api.query(query, org=self.org)
        
        remaining_channels = set(target_channels)
        for table in tables:
            if len(remaining_channels) <= 0:
                break
            for record in (reversed(table.records) if lastonly else table.records):
                if len(remaining_channels) <= 0:
                    break
                if schema.tag is None:
                    # no tag: channel as field
                    channel = record.get_field()
                else:
                    # tag and fields
                    tag_value = record.values[schema.tag]
                    field = record.get_field()
                    channel = '%s%s%s' % (tag_value, Schema.tag_field_separator, field)
                    channel = name_mapping.get(channel, channel)
                if channel in remaining_channels:
                    if lastonly:
                        remaining_channels.remove(channel)
                    channel += schema.suffix
                    if channel not in result:
                        result[channel] = {
                            'start': start, 'length': int(length), 't': [], 'x': []
                        }
                    value = DataSource.decode_if_json(record.get_value())
                    result[channel]['t'].append(int(1000*(record.get_time().timestamp()-start))/1000.0)
                    result[channel]['x'].append(value)

        return result
