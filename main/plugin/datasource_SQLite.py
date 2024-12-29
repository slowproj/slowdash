# Created by Sanshiro Enomoto on 10 April 2023 #


import sys, os, logging
from datasource_SQL import SQLServer, DataSource_SQL

import sqlite3


class DataSource_SQLite(DataSource_SQL):
    def __init__(self, app, project, params):
        super().__init__(app, project, params)
        
        self.time_sep = ' '
        self.db_has_floor = False
        
        url = params.get('url', '')
        if url[0:10] == 'sqlite:///':
            filename = url[10:]
        else:
            filename = ''
            
        filename = params.get('file', filename)
        if filename[-3:] == '.db':
            self.db_name = filename[0:-3]
        else:
            self.db_name = filename


    def connect(self):
        if self.db_name is None:
            return super().connect()
            
        try:
            conn = sqlite3.connect('%s.db' % self.db_name)
        except Exception as e:
            logging.error('DB "%s" cannot be connnected: %s' % (db_name, str(e)))
            return None
        if conn is None:
            return None
        
        logging.debug('SQLite: DB connected: "%s.db"' % self.db_name)
        
        return SQLServer(conn)
