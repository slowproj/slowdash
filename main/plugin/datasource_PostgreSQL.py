# Created by Sanshiro Enomoto on 10 April 2023 #


import sys, os, logging
from datasource_SQL import SQLServer, DataSource_SQL

import psycopg2 as db


class DataSource_PostgreSQL(DataSource_SQL):
    def __init__(self, app, project, params):
        super().__init__(app, project, params)
        
        self.db_has_floor = True
        
        self.url = params.get('url', None)
        if self.url is not None and self.url[0:13] != 'postgresql://':
            self.url = 'postgresql://' + self.url
        

    def connect(self):
        if self.url is None:
            return super().connect()
        
        try:
            conn = db.connect(self.url)
        except Exception as e:
            logging.error("PostgreSQL: %s: %s" % (self.url, str(e)))
            return None
        if conn is None:
            return None

        logging.info('PostgreSQL: DB connected: "%s"' % self.url)
        
        return SQLServer(conn)
