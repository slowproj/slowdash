# Created by Sanshiro Enomoto on 10 April 2023 #


import sys, os, logging
from sd_datasource_SQL import SQLServer, DataSource_SQL

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

        db_file = '%s.db' % self.db_name
        if not os.path.isfile(db_file):
            logging.info(f'SQLite: DB file does not exist: "{db_file}"')
            return None
        
        try:
            conn = sqlite3.connect(db_file)
        except Exception as e:
            logging.error(f'DB "db_file" cannot be connnected: {str(e)}')
            return None
        if conn is None:
            return None
        
        logging.debug(f'SQLite: DB connected: "{db_file}"')
        
        return SQLServer(conn)
