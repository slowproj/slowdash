import logging

from .base import DataStore, DataStore_Null
from .store_SQL import DataStore_PostgreSQL, DataStore_SQLite
from .store_InfluxDB2 import DataStore_InfluxDB2
from .store_Redis import DataStore_Redis
from .store_CSV import DataStore_CSV, DataStore_TextDump


def create_datastore_from_url(url, *args, **kwargs):
    if url.startswith('postgresql://'):
        return DataStore_PostgreSQL(db_url=url, table=args[0])
    elif url.startswith('sqlite://'):
        return DataStore_SQLite(db_url=url, table=args[0])
    elif url.startswith('influxdb2://'):
        return DataStore_InfluxDB2(db_url=url, measurement=args[0])
    elif url.startswith('redis://'):
        return DataStore_Redis(db_url=url)
    elif url.startswith('csv:///'):
        return DataStore_CSV(db_url, table=args[0])
    elif url.startswith('dump:///'):
        return DataStore_TextDump()

    logging.error('unknown datastore type: %s' % url)
    return DataStore_Null()
