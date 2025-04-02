# Created by Sanshiro Enomoto on 3 June 2023 #


import os, sys, time, logging, traceback
from urllib.parse import urlparse
from .base import DataStore


class TableFormat:
    def __init__(self):
        self.db = None
        self.table = None

    
    def bind(self, db, table):
        self.db = db
        self.table = table

        
    # override as needed
    def create_table(self, cur, tag, fields, values):
        if self.table is None or len(values) == 0:
            return False

        result = False
        try:
            if type(values[0]) in [ int, float ]:
                result = self.create_numeric_table(cur)
            else:
                result = self.create_text_table(cur)
        except Exception as e:
            result = False

        return result

    
    # to be implemented in a subclass    
    def create_numeric_table(self, cur):
        return False

    
    # to be implemented in a subclass    
    def create_text_table(self, cur):
        return False

    
    # override as needed
    def write(self, cur, timestamp, tag, fields, values, update):
        channels = DataStore._channels(tag, fields)
        try:
            for i in range(min(len(channels), len(values))):
                self.write_single(cur, timestamp, channels[i], values[i], update)
        except Exception as e:
            logging.error('SQL Error: %s' % str(e))

            
    # override as needed
    def write_single(self, cur, timestamp, channel, value, update):
        if update is True:
            # DELETE and INSERT (in a transaction):
            # this is worse than UPSERT, as DELETE/INSERT might trigger re-indexing,
            # but there is no reliable standard way for UPSERT usable in all RDBMS...
            sql = f"DELETE FROM {self.table} WHERE channel={self.db.placeholder}"
            cur.execute(sql, (channel,))            
        if type(value) in [int, float]:
            self.insert_numeric_data(cur, timestamp, channel, value)
        else:
            self.insert_text_data(cur, timestamp, channel, value)

            
    # to be implemented in a subclass
    def insert_numeric_data(self, cur, timestamp, channel, value):
        pass

    
    # to be implemented in a subclass
    def insert_text_data(self, cur, timestamp, channel, value):
        pass
    

    
class LongTableFormat(TableFormat):
    # these can be overriden. Set None to disable table creation
    # Note: REAL is 64 bit in MySQL and SQLite. For PostgreSQL, timestamp will be DateTime with TimeZone.
    schema_numeric = '(timestamp REAL, channel VARCHAR(100), value REAL, PRIMARY KEY(timestamp,channel))'
    schema_text = '(timestamp REAL, channel VARCHAR(100), value TEXT, PRIMARY KEY(timestamp,channel))'

    
    def create_numeric_table(self, cur):
        if self.schema_numeric is None:
            return False
        else:
            cur.execute(f'CREATE TABLE {self.table}{self.schema_numeric}')
            return True

    
    def create_text_table(self, cur):
        if self.schema_text is None:
            return False
        else:
            cur.execute(f'CREATE TABLE {self.table}{self.schema_text}')
            return True


    def insert_numeric_data(self, cur, timestamp, channel, value):
        sql = f"INSERT INTO {self.table}(timestamp,channel,value) "
        sql += f"VALUES(%.3f,%s,%f);" % (timestamp, self.db.placeholder, value)
        params = (channel,)
        cur.execute(sql, params)

        
    def insert_text_data(self, cur, timestamp, channel, value):
        sql = f"INSERT INTO {self.table}(timestamp,channel,value) "
        sql += f"VALUES(%.3f,%s,%s);" % (timestamp, self.db.placeholder, self.db.placeholder)
        params = (channel, str(value))
        cur.execute(sql, params)
            
            

class LongTableFormat_DateTime_PostgreSQL(LongTableFormat):
    schema_numeric = '("timestamp" TIMESTAMP WITH TIME ZONE , channel VARCHAR(100), value REAL, PRIMARY KEY(timestamp,channel))'
    schema_text = '("timestamp" TIMESTAMP WITH TIME ZONE, channel VARCHAR(100), value TEXT, PRIMARY KEY(timestamp,channel))'

    
    def insert_numeric_data(self, cur, timestamp, channel, value):
        sql = f"INSERT INTO {self.table}(timestamp,channel,value) "
        sql += f"VALUES(TO_TIMESTAMP(%.3f),%s,%f);" % (timestamp, self.db.placeholder, value)
        params = (channel,)
        cur.execute(sql, params)

        
    def insert_text_data(self, cur, timestamp, channel, value):
        sql = f"INSERT INTO {self.table}(timestamp,channel,value) "
        sql += f"VALUES(TO_TIMESTAMP(%.3f),%s,%s);" % (timestamp, self.db.placeholder, self.db.placeholder)
        params = (channel, str(value))
        cur.execute(sql, params)
        


class LongTableFormat_DateTime_MySQL(LongTableFormat):
    # timestamp in MySQL is stored in UTC. As of Mar 2025, pymysql and aiomysql cannot handle this properly
    # (treated as "naive"), so if this format is used, use "unspecified utc" time type in SlowDash.
    schema_numeric = '(timestamp TIMESTAMP , channel VARCHAR(100), value REAL, PRIMARY KEY(timestamp,channel))'
    schema_text = '(timestamp TIMESTAMP, channel VARCHAR(100), value TEXT, PRIMARY KEY(timestamp,channel))'

    
    def insert_numeric_data(self, cur, timestamp, channel, value):
        sql = f"INSERT INTO {self.table}(timestamp,channel,value) "
        sql += f"VALUES(FROM_UNIXTIME(%.3f),%s,%f);" % (timestamp, self.db.placeholder, value)
        params = (channel,)
        cur.execute(sql, params)

        
    def insert_text_data(self, cur, timestamp, channel, value):
        sql = f"INSERT INTO {self.table}(timestamp,channel,value) "
        sql += f"VALUES(FROM_UNIXTIME(%.3f),%s,%s);" % (timestamp, self.db.placeholder, self.db.placeholder)
        params = (channel, str(value))
        cur.execute(sql, params)
        


        
class DataStore_SQL(DataStore):
    # to be implemented in a subclass
    placeholder = '?'
    def construct(self):
        return None # conn
    def get_table_list(self):
        return []
    
    
    def __init__(self, db_url, table, table_format, lazy_construction=False):
        self.lazy_construction = lazy_construction
        
        self.table = None
        self.conn = None
        
        if not table.replace('_', '').isalnum():
            logging.error('SQL: bad table name "%s"' % table)
            return
        
        self.db_url = db_url
        self.table = table
        self.table_format = table_format
        self.table_format.bind(self, table)

        if self.lazy_construction:
            return
        
        self.conn = self.construct()
        if self.conn is None:
            self.table_exists = None
            return
        
        table_list = [ name.upper() for name in self.get_table_list() ]
        self.table_exists = (self.table is not None) and (self.table.upper() in table_list)


    def __del__(self):
        self.close()


    def close(self):
        if self.conn is not None:
            self.conn.close()
            self.conn = None
            logging.info('DB "%s" is disconnnected.' % self.db_url)

            
    def _write(self, values, tag=None, timestamp=None, update=False):
        if self.lazy_construction:
            self.lazy_construction = False
            self.conn = self.construct()
            if self.conn is None:
                self.table_exists = None
        
        super()._write(values, tag, timestamp, update)

        
    def _write_one(self, cur, timestamp, tag, fields, values, update):
        table_list = [ name.upper() for name in self.get_table_list() ]
        self.table_exists = (self.table is not None) and (self.table.upper() in table_list)
                    
        if self.table_exists is False:
            self.table_exists = self.table_format.create_table(cur, tag, fields, values)
            if not self.table_exists:
                self.table_exists = None  # no further retrying
                return

        self.table_format.write(cur, timestamp, tag, fields, values, update)

                    
        
class DataStore_SQLite(DataStore_SQL):
    placeholder = '?'
    
    def __init__(self, db_url, table, table_format=None):
        
        if table_format is None:
            table_format = LongTableFormat()
            
        # lazy_construction is enabled so that the same thread is used for both connect() and write()
        super().__init__(db_url, table, table_format, lazy_construction=True)
        

    def another(self, table, table_format=None):
        if table_format is None:
            table_format = type(self.table_format)()
            
        return DataStore_SQLite(self.db_url, table, table_format)
        
        
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

    
    def _open_transaction(self):
        if self.conn is None:
            return None
        cur = self.conn.cursor()
        cur.execute('BEGIN TRANSACTION;')
        return cur
        
    
    def _close_transaction(self, cur):
        try:
            self.conn.commit()
        except Exception as e:
            logging.error('SQL commit(): %s' % str(e))
        del cur

    
    
class DataStore_PostgreSQL(DataStore_SQL):
    placeholder = '%s'
        
    def __init__(self, db_url, table, table_format=None):
        if table_format is None:
            table_format = LongTableFormat_DateTime_PostgreSQL()
        super().__init__(db_url, table, table_format)

        
    def another(self, table, table_format=None):
        if table_format is None:
            table_format = type(self.table_format)()
            
        return DataStore_PostgreSQL(self.db_url, table, table_format)
        
        
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
            result = [ table_name[0] for table_name in cur.fetchall() ]
        except Exception as e:
            logging.error('PostgreSQL: unable to get table list: %s: %s' % (self.db_url, str(e)))
            result = []
        cur.close()
        
        return result
    

    def _open_transaction(self):
        if self.conn is None:
            return None
        return self.conn.cursor()
        
    
    def _close_transaction(self, cur):
        try:
            self.conn.commit()
        except Exception as e:
            logging.error('SQL commit(): %s' % str(e))
        del cur


        
class DataStore_MySQL(DataStore_SQL):
    placeholder = '%s'
        
    def __init__(self, db_url, table, table_format=None):
        if table_format is None:
            # MySQL TIMESTAMP uses UTC, but pymysql cannot handle timezone (treat the time as "native")
            table_format = LongTableFormat()
            #table_format = LongTableFormat_DateTime_MySQL()
        super().__init__(db_url, table, table_format)

        
    def another(self, table, table_format=None):
        if table_format is None:
            table_format = type(self.table_format)()
            
        return DataStore_MySQL(self.db_url, table, table_format)
        
        
    def construct(self):
        db_url = self.db_url
        if not db_url.startswith('mysql://'):
            db_url = 'mysql://' + db_url

        parsed = urlparse(db_url)
        user = parsed.username
        password = parsed.password
        host = parsed.hostname
        port = parsed.port or 3306
        db = parsed.path.lstrip('/')
            
        #import pymysql as mysql
        import mysql.connector as mysql
        
        logging.info('connecting to %s...' % db_url)
        for i in range(12):
            try:
                self.conn = mysql.connect(host=host, port=port, user=user, password=password, db=db)
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
            cur.execute("SHOW TABLES")
            result = [ table_name[0] for table_name in cur.fetchall() ]
        except Exception as e:
            logging.error('MySQL: unable to get table list: %s: %s' % (self.db_url, str(e)))
            result = []
        cur.close()
        
        return result
    

    def _open_transaction(self):
        if self.conn is None:
            return None
        return self.conn.cursor()
        
    
    def _close_transaction(self, cur):
        try:
            self.conn.commit()
        except Exception as e:
            logging.error('SQL commit(): %s' % str(e))
        del cur
