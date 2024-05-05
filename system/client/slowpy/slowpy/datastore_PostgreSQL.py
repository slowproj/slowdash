# Created by Sanshiro Enomoto on 3 May 2024 #


import os, sys, time, logging
from .datastore import DataStore


class DataStore_PostgreSQL(DataStore):
    schema_ts = '(timestamp INTEGER, channel TEXT, value REAL, PRIMARY KEY(timestamp, channel))'
    schema_obj = '(channel TEXT, value TEXT, PRIMARY KEY(channel))'
    schema_objts = '(timestamp INTEGER, channel TEXT, value TEXT, PRIMARY KEY(timestamp, channel))'

    def __init__(self, db_url='postgresql://postgres:postgres@localhost:5432/SlowStore', table_name=None, obj_table_name=None, objts_table_name=None):
        
        #### START OF PGSQL-SPECIFIC ####
        
        self.db_url = db_url if db_url.startswith('postgresql://') else 'postgresql://' + db_url
            
        table_basename = table_name if table_name is not None else 'slowpy'
        self.ts_table_name = table_name if table_name is not None else table_basename+'_ts'
        self.obj_table_name = obj_table_name if obj_table_name is not None else table_basename+'_obj'
        self.objts_table_name = objts_table_name if objts_table_name is not None else table_basename+'_objts'

        self.conn = None
        import psycopg2 as pg2
        tries = 0
        while tries < 10:
            try:
                self.conn = pg2.connect(self.db_url)
                break
            except Exception as e:
                self.conn = None
                logging.error('PostgreSQL: %s: %s', self.db_url, str(e))
                tries = tries + 1
                time.sleep(10)
        if self.conn is None:
            return
        logging.info('DB "%s" is connnected.' % self.db_url)

        
        cur = self.conn.cursor()
        try:
            cur.execute("select tablename from pg_tables where schemaname='public'")
        except Exception as e:
            logging.error('PostgreSQL: unable to get table list: %s: %s', self.db_url, str(e))

        table_list = [ table_name[0] for table_name in cur.fetchall() ]

        #### END OF PGSQL-SPECIFIC ####

        
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


    def another(self, db_url=None, table_name=None, obj_table_name=None, objts_table_name=None):
        if db_url is None:
            db_url = self.db_url
        if table_name is None:
            table_name = self.table_name
        if obj_table_name is None:
            obj_table_name = self.obj_table_name
        if objts_table_name is None:
            objts_table_name = self.objts_table_name
            
        return DataStore_PostgreSQL(db_url, table_name, obj_table_name, objts_table_name)
        

    def write_timeseries(self, fields, tag=None, timestamp=None):
        if self.conn is None:
            return
        cur = self.conn.cursor()
        
        if timestamp is None:
            timestamp = time.time()

        if not isinstance(fields, dict):
            if tag is None:
                return
            cur.execute("INSERT INTO %s VALUES(%d,'%s',%f)" % (self.ts_table_name, timestamp, tag, fields))
        else:
            for k, v in fields.items():
                ch = k if tag is None else "%s:%s" % (tag, k)
                cur.execute("INSERT INTO %s VALUES(%d,'%s',%f)" % (self.table_name, timestamp, ch, v))
        self.conn.commit()
                    
    
    def write_object(self, obj, name=None):
        if self.conn is None:
            return
        if self.obj_table_name is None:
            return

        if name is None:
            name = obj.name

        cur = self.conn.cursor()
        cur.execute(
            # this UPSERT is PostgreSQL specific (>= 9.5), similar to SQLite, different from MySQL
            '''INSERT INTO %s(channel,value) VALUES('%s','%s') ON CONFLICT(channel) DO UPDATE SET value=excluded.value''' %
            (self.obj_table_name, name, str(obj))
        )
        self.conn.commit()

        
    def write_object_timeseries(self, obj, timestamp=None, name=None):
        if self.conn is None:
            return
        if self.objts_table_name is None:
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
