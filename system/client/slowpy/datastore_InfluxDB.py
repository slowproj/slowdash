# Created by Sanshiro Enomoto on 14 June 2023 #

import datetime
from .datastore import DataStore


class DataStore_InfluxDB(DataStore):
    def __init__(self, url, org, token, bucket, measurement, use_tag=True):
        from influxdb_client import InfluxDBClient, Point
        from influxdb_client.client.write_api import SYNCHRONOUS, WritePrecision

        self.url = url
        self.org = org
        self.token = token
        self.bucket = bucket
        self.measurement = measurement
        self.use_tag = use_tag
        
        self.client = InfluxDBClient(url=url, org=org, token=token)
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)

        self.Point = Point
        self.write_precision = WritePrecision.S

        
    def __del__(self):
        self.client.close()


    def another(self, measurement=None):
        if measurement is None:
            measurement = self.measurement
        return DataStore_InfluxDB(self.url, self.org, self.token, self.bucket, measurement)

    
    def write_timeseries(self, fields, tag=None, timestamp=None):
        if self.use_tag and tag is None:
            for key, value in fields.items():
                self._write(value, key, timestamp, float)
        else:
            self._write(fields, tag, timestamp, float)

        
    def write_object_timeseries(self, obj, timestamp=None, name=None):
        if name is None:
            name = obj.name
        self._write(str(obj), name, timestamp, str)

        
    def _write(self, fields, tag, timestamp, datatype):
        point = self.Point(self.measurement)
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
