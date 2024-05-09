# Created by Sanshiro Enomoto on 3 June 2023 #


import os, sys, time, logging
from .datastore import DataStore


class DataStore_SQL(DataStore):
    schema_ts = '(timestamp INTEGER, channel TEXT, value REAL, PRIMARY KEY(timestamp, channel))'
    schema_obj = '(channel TEXT, value TEXT, PRIMARY KEY(channel))'
    schema_objts = '(timestamp INTEGER, channel TEXT, value TEXT, PRIMARY KEY(timestamp, channel))'

    # to be implemented in a subclass
    def construct(self):
        return None # conn
    def get_table_list(self):
        return []
    
    
    def __init__(self, db_url='sqlite:///SlowStore.db', ts_table_name=None, obj_table_name=None, objts_table_name=None):
        self.db_url = db_url
        self.ts_table_name = ts_table_name
        self.obj_table_name = obj_table_name
        self.objts_table_name = objts_table_name
        
        self.conn = self.construct()
        if self.conn is None:
            return
        
        table_list = self.get_table_list()
        cur = self.conn.cursor()
        if self.ts_table_name is not None and self.ts_table_name not in table_list:
            logging.info('Creating a new time-series data table "%s"...' % self.ts_table_name)
            cur.execute('CREATE TABLE %s%s' % (self.ts_table_name, self.schema_ts))
            self.conn.commit()
        if self.obj_table_name is not None and self.obj_table_name not in table_list:
            logging.info('Creating a new object data table "%s"...' % self.obj_table_name)
            cur.execute('CREATE TABLE %s%s' % (self.obj_table_name, self.schema_obj))
            self.conn.commit()
        if self.objts_table_name is not None and self.objts_table_name not in table_list:
            logging.info('Creating a new object-timeseries data table "%s"...' % self.objts_table_name)
            cur.execute('CREATE TABLE %s%s' % (self.objts_table_name, self.schema_objts))
            self.conn.commit()

            
    def __del__(self):
        if self.conn is not None:
            self.conn.close()
            logging.info('DB "%s" is disconnnected.' % self.db_url)


    def write_timeseries(self, fields, tag=None, timestamp=None):
        if (self.conn is None) or (self.ts_table_name is None):
            return
        
        if timestamp is None:
            timestamp = time.time()

        cur = self.conn.cursor()
        if not isinstance(fields, dict):
            if tag is None:
                return
            cur.execute("INSERT INTO %s VALUES(%d,'%s',%f)" % (self.ts_table_name, timestamp, tag, fields))
        else:
            for k, v in fields.items():
                ch = k if tag is None else "%s:%s" % (tag, k)
                cur.execute("INSERT INTO %s VALUES(%d,'%s',%f)" % (self.ts_table_name, timestamp, ch, v))
        self.conn.commit()
                    
    
    def write_object(self, obj, name=None):
        if (self.conn is None) or (self.obj_table_name is None):
            return

        if name is None:
            name = obj.name

        cur = self.conn.cursor()
        cur.execute(
            # this UPSERT is SQLite & PostgreSQL(>=9.5) specific, different from MySQL
            '''INSERT INTO %s(channel,value) VALUES('%s','%s') ON CONFLICT(channel) DO UPDATE SET value=excluded.value''' %
            (self.obj_table_name, name, str(obj))
        )
        self.conn.commit()

        
    def write_object_timeseries(self, obj, timestamp=None, name=None):
        if (self.conn is None) or (self.objts_table_name is None):
            return
        
        if timestamp is None:
            timestamp = time.time()
        if name is None:
            name = obj.name
            
        cur = self.conn.cursor()
        cur.execute(
            '''INSERT INTO %s VALUES(%d,'%s','%s')''' %
            (self.objts_table_name, timestamp, name, str(obj))
        )
        self.conn.commit()


        
class DataStore_SQLite(DataStore_SQL):
    def __init__(self, db_url='sqlite:///SlowStore.db', ts_table_name=None, obj_table_name=None, objts_table_name=None):
        super().__init__(db_url, ts_table_name, obj_table_name, objts_table_name)

    def construct(self):
        db_url = self.db_url
        if db_url.startswith('sqlite:///'):
            db_url = db_url[10:]
        if db_url.endswith('.db'):
            db_url = db_url[0:-3]
            
        import sqlite3
        if not os.path.exists('%s.db' % db_url):
            logging.info('DB file "%s.db" does not exist. Creating...' % self.db_url)
        self.conn = sqlite3.connect('%s.db' % db_url)
        
        logging.info('DB "%s" is connnected.' % self.db_url)
        return self.conn

        
    def get_table_list(self):
        if self.conn is None:
            return []
            
        cur = self.conn.cursor()
        try:
            cur.execute('select name from sqlite_master where type="table"')
        except Exception as e:
            logging.error('SQLite: unable to get table list: %s: %s', self.db_url, str(e))
            return []
        
        return [ table_name[0] for table_name in cur.fetchall() ]

    


class DataStore_PostgreSQL(DataStore_SQL):
    def __init__(self, db_url='postgresql://postgres:postgres@localhost:5432/SlowStore', ts_table_name=None, obj_table_name=None, objts_table_name=None):
        super().__init__(db_url, ts_table_name, obj_table_name, objts_table_name)
        
    def construct(self):
        db_url = self.db_url
        if not db_url.startswith('postgresql://'):
            db_url = 'postgresql://' + db_url
            
        logging.info('connecting to %s...' % db_url)
        import psycopg2 as pg2
        for i in range(12):
            try:
                self.conn = pg2.connect(db_url)
                break
            except Exception as e:
                logging.warn(e)
                logging.warn('retrying in 5 sec...')
                time.sleep(5)
        else:
            self.conn = None
            logging.error('Unable to connect to PostgreSQL')
            logging.error(traceback.format_exc())
            return
        
        logging.info('DB "%s" is connnected.' % self.db_url)
        return self.conn

        
    def get_table_list(self):
        if self.conn is None:
            return []
        
        cur = self.conn.cursor()
        try:
            cur.execute("select tablename from pg_tables where schemaname='public'")
        except Exception as e:
            logging.error('PostgreSQL: unable to get table list: %s: %s', self.db_url, str(e))
            return []

        return [ table_name[0] for table_name in cur.fetchall() ]
