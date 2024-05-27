# Created by Sanshiro Enomoto on 14 June 2023 #

import datetime
from .datastore import DataStore


class DataStore_InfluxDB2(DataStore):
    # URL: influxdb2://org:token@host:port/bucket
    def __init__(self, url, ts_measurement=None, obj_measurement=None, objts_measurement=None, use_tag=True):
        from influxdb_client import InfluxDBClient, Point
        from influxdb_client.client.write_api import SYNCHRONOUS, WritePrecision

        self.url = url
        self.ts_measurement = ts_measurement
        self.obj_measurement = obj_measurement
        self.objts_measurement = objts_measurement
        self.use_tag = use_tag
        
        if url.startswith('influxdb2://'):
            url = url[12:]
        split_at = url.rsplit('@', 1)
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
            
        self.org = org
        self.bucket = bucket
        
        for i in range(12):
            try:
                self.client = InfluxDBClient(url='http://%s:%s'%(host,port), org=self.org, token=token)
                self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
                break
            except Exception as e:
                logging.warn(e)
                logging.warn('Unable to connect to the Db server. Retrying in 5 sec...')
                time.sleep(5)
        else:
            self.conn = None
            logging.error('Unable to connect to the InfluxDB server')
            logging.error(traceback.format_exc())
            return

        self.Point = Point
        self.write_precision = WritePrecision.S

        
    def __del__(self):
        self.client.close()


    def write_timeseries(self, fields, tag=None, timestamp=None):
        if self.ts_measurement is None:
            return
        if self.use_tag and tag is None:
            for key, value in fields.items():
                self._write(self.ts_measurement, value, key, timestamp, float)
        else:
            self._write(self.ts_measurement, fields, tag, timestamp, float)

        
    def write_object(self, obj, timestamp=None, name=None):
        if self.obj_measurement is None:
            return
        if name is None:
            name = obj.name
        self._write(self.obj_measurement, str(obj), name, timestamp, str)

        
    def write_object_timeseries(self, obj, timestamp=None, name=None):
        if self.objts_measurement is None:
            return
        if name is None:
            name = obj.name
        self._write(self.objts_measurement, str(obj), name, timestamp, str)

        
    def _write(self, measurement, fields, tag, timestamp, datatype):
        point = self.Point(measurement)
        if tag is not None:
            point = point.tag("channel", tag)
            
        if timestamp is not None:
            if type(timestamp) in [ float, int ]:
                timestamp = datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc)
            point.time(timestamp, self.write_precision)
            
        if not isinstance(fields, dict):
            if tag is None:
                return
            point = point.field('value', datatype(fields))
        else:
            for key, value in fields.items():
                point = point.field(key, datatype(value))
                
        #print(point)
        self.write_api.write(self.bucket, self.org, point)
