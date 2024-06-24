# Created by Sanshiro Enomoto on 3 June 2023 #


import os, sys, time, logging
from .base import DataStore


class SimpleLongFormatInserter:
    schema_numeric = '(timestamp REAL, channel TEXT, value REAL, PRIMARY KEY(timestamp,channel))'
    schema_text = '(timestamp REAL, channel TEXT, value TEXT, PRIMARY KEY(timestamp,channel))'

    def __init__(self, table_name):
        self.table_name = table_name
        self.placeholder = '?'
        self.floating_type = 'REAL'
            
    
    def create_table(self, cur, tag, fields, values):
        if self.table_name is None or len(values) == 0:
            return False

        if type(values[0]) in [ int, float ]:
            schema = self.schema_numeric.replace('REAL', self.floating_type)
        else:
            schema = self.schema_text.replace('REAL', self.floating_type)
        try:
            cur.execute('CREATE TABLE %s%s;' % (self.table_name, schema))
        except Exception as e:
            logging.error('SQL: unable to create table "%s": %s' % (self.table_name, str(e)))
            return False
        
        return True


    def write_one(self, cur, timestamp, tag, fields, values, update):
        channels = DataStore._channels(tag, fields)
        for i in range(min(len(channels), len(values))):
            ch, value = channels[i], values[i]

            if update is True:
                sql = f"DELETE FROM {self.table_name} WHERE channel={self.placeholder} "
                sql += f"AND EXISTS (SELECT 1 FROM {self.table_name} WHERE channel={self.placeholder});"
                cur.execute(sql, (ch, ch))
            
            sql = f"INSERT INTO {self.table_name}(timestamp,channel,value) "
            if type(value) in [int, float]:
                sql += f"VALUES(%.3f,%s,%f);" % (timestamp, self.placeholder, value)
                params = (ch,)
            else:
                sql += f"VALUES(%.3f,%s,%s);" % (timestamp, self.placeholder, self.placeholder)
                params = (ch, str(value))
            try:
                cur.execute(sql, params)
            except Exception as e:
                logging.error('SQL execute(): %s' % str(e))

            

class DataStore_SQL(DataStore):
    # to be implemented in a subclass
    def construct(self):
        return None # conn
    def get_table_list(self):
        return []
    
    
    def __init__(self, db_url, table_name, Inserter=SimpleLongFormatInserter):        
        if not table_name.replace('_', '').isalnum():
            logging.error('SQL: bad table name "%s"' % table_name)
            self.table_name = None
            self.conn = None
            return
        
        self.db_url = db_url
        self.table_name = table_name
        self.inserter = Inserter(self.table_name)
        
        self.conn = self.construct()
        if self.conn is None:
            return
        
        table_list = [ name.upper() for name in self.get_table_list() ]
        self.table_exists = (self.table_name is not None) and (self.table_name.upper() in table_list)

        
    def __del__(self):
        if self.conn is not None:
            self.conn.close()
            logging.info('DB "%s" is disconnnected.' % self.db_url)


    def _open_transaction(self):
        if self.conn is None:
            return False
        cur = self.conn.cursor()
        cur.execute('BEGIN TRANSACTION;')
        return cur
        
    
    def _close_transaction(self, cur):
        try:
            self.conn.commit()
        except Exception as e:
            logging.error('SQL commit(): %s' % str(e))
            
        del cur

    
    def _write_one(self, cur, timestamp, tag, fields, values, update):
        if not self.table_exists:
            self.table_exists = self.inserter.create_table(cur, tag, fields, values)
            if not self.table_exists:
                return

        self.inserter.write_one(cur, timestamp, tag, fields, values, update)

                    
        
class DataStore_SQLite(DataStore_SQL):
    def __init__(self, db_url, table_name, Inserter=SimpleLongFormatInserter):
        super().__init__(db_url, table_name, Inserter)
        self.inserter.placeholder = '?'
        self.inserter.floating_type = 'REAL'

        
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
            cur.execute('select name from sqlite_master where type="table";')
        except Exception as e:
            logging.error('SQLite: unable to get table list: %s: %s' % (self.db_url, str(e)))
            return []
        
        return [ table_name[0] for table_name in cur.fetchall() ]

    


class DataStore_PostgreSQL(DataStore_SQL):
    def __init__(self, db_url, table_name, Inserter=SimpleLongFormatInserter):
        super().__init__(db_url, table_name, Inserter)
        self.inserter.placeholder = '%s'
        self.inserter.floating_type = 'DOUBLE PRECISION'

        
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
                logging.warn('Unable to connect to the Db server. Retrying in 5 sec...')
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
            cur.execute("select tablename from pg_tables where schemaname='public';")
        except Exception as e:
            logging.error('PostgreSQL: unable to get table list: %s: %s' % (self.db_url, str(e)))
            return []

        return [ table_name[0] for table_name in cur.fetchall() ]
