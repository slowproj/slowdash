# Created by Sanshiro Enomoto on 14 June 2023 #

import time, datetime, traceback, logging
from .base import DataStore


class DataStore_InfluxDB2(DataStore):
    def __init__(self, db_url, measurement, tag_column='channel', field='value'):
        '''
        - db_url: influxdb2://org:token@host:port/bucket
        - tag_column: name of the tag column, None for not using tags (wide format)
        - field: name of the value field for the long format, or None for the wide format (fields specified by data)
        Use a different measurement or field for different data types (e.g., numerical values and histograms)
        '''
    
        from influxdb_client import InfluxDBClient, Point
        from influxdb_client.client.write_api import SYNCHRONOUS, WritePrecision

        self.url = db_url
        self.measurement = measurement
        self.tag_column = tag_column
        self.field = field
        
        if db_url.startswith('influxdb2://'):
            db_url = db_url[12:]
        split_at = db_url.rsplit('@', 1)
        if  len(split_at) < 2:
            org, token = '', ''
        else:
            split_at_colon = split_at[0].split(':', 1)
            if len(split_at_colon) < 2:
                org, token = split_at_colon[0], ''
            else:
                org, token = split_at_colon[0], split_at_colon[1]
        split_at_slash = split_at[1].split('/', 1)
        if len(split_at_slash) < 2:
            bucket = ''
        else:
            bucket = split_at_slash[1]
        split_at_slash_colon = split_at_slash[0].split(':', 1)
        if len(split_at_slash_colon) < 2:
            host, port = split_at_slash, '8086'
        else:
            host, port = split_at_slash_colon[0], split_at_slash_colon[1]
            
        self.bucket = bucket
        self.org = org

        self.client = None
        for i in range(12):
            try:
                self.client = InfluxDBClient(url='http://%s:%s'%(host,port), org=self.org, token=token)
                buckets = self.client.buckets_api().find_buckets().buckets
                break
            except Exception as e:
                logging.warn(e)
                logging.warn('Unable to connect to the Db server. Retrying in 5 sec...')
                time.sleep(5)
        else:
            self.client = None
            logging.error('Unable to connect to the InfluxDB server')
            logging.error(traceback.format_exc())
            return

        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.Point = Point
        self.write_precision = WritePrecision.S
        self.update_error_shown = False

        
    def __del__(self):
        self.close()


    def close(self):
        if self.client is not None:
            self.client.close()
            self.client = None


    def another(self, measurement='', tag_column='', field=''):
        if measurement == '':
            measurement = self.measurement
        if tag_column == '':
            tag_column = self.tag_column
        if field == '':
            field = self.field
            
        return DataStore_InfluxDB2(self.url, measurement, tag_column, field)
    
        
    def _open_transaction(self):
        if self.measurement is None or self.write_api is None:
            return False
        
        return self.measurement
    
        
    def _close_transaction(self, measurement):
        pass

    
    def _write_one(self, measurement, timestamp, tag, fields, values, update):
        if update is True and self.update_error_shown is False:
            logging.error('InfluxDB2: "update()" is not available for InfluxDB: switched to append()')
            self.update_error_shown = True
        
        if self.field is not None:  # long format
            channels = self._channels(tag, fields)
            for i in range(min(len(channels), len(values))):
                self._write_point(measurement, timestamp, tag=channels[i], fields=[self.field], values=[values[i]])
                
        elif fields is not None:   # wide format, fields from data
            self._write_point(measurement, timestamp, tag, fields, values)
                
        else:                      # field not given: long format with a fallback field name
            self._write_point(measurement, timestamp, tag, fields=['__value']*len(values), values=values)
            
            
    def _write_point(self, measurement, timestamp, tag, fields, values):
        point = self.Point(measurement)
            
        if timestamp is not None:
            if type(timestamp) in [ float, int ]:
                timestamp = datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc)
            point.time(timestamp, self.write_precision)
            
        if self.tag_column is not None and tag is not None:
            point = point.tag(self.tag_column, tag)

        for i in range(min(len(fields), len(values))):
            if type(values[i]) in [ int, float ]:
                point = point.field(fields[i], values[i])
            else:
                point = point.field(fields[i], str(values[i]))
            
        #print(point)
        self.write_api.write(self.bucket, self.org, point)

