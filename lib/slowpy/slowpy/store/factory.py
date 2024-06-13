import logging

from .base import DataStore, DataStore_Null
from .store_SQL import DataStore_PostgreSQL,  DataStore_SQLite
from .store_InfluxDB2 import DataStore_InfluxDB2
from .store_Redis import DataStore_Redis
from .store_CSV import DataStore_CSV, DataStore_TextDump


def create_datastore_from_url(url, ts_name=None, obj_name=None, objts_name=None, **kwargs):
    if url.startswith('postgresql://'):
        return DataStore_PostgreSQL(url, ts_name, obj_name, objts_name, **kwargs)
    elif url.startswith('sqlite://'):
        return DataStore_SQLite(url, ts_name, obj_name, objts_name, **kwargs)
    elif url.startswith('influxdb2://'):
        return DataStore_InfluxDB2(url, ts_name, obj_name, objts_name, **kwargs)
    elif url.startswith('redis://'):
        return DataStore_Redis(url, **kwargs)
    elif url.startswith('csv:///'):
        return DataStore_CSV(url, ts_name, obj_name, objts_name, **kwargs)
    elif url.startswith('dump:///'):
        return DataStore_TextDump(**kwargs)

    logging.error('unknown datastore type: %s' % url)
    return DataStore_Null()
