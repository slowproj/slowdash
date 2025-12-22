# Created by Sanshiro Enomoto on 10 April 2023 #


import sys, os, logging
from sd_datasource_SQL import SQLServer, DataSource_SQL

import psycopg2 as db


class DataSource_PostgreSQL_NoAsync(DataSource_SQL):
    def __init__(self, app, project, params):
        super().__init__(app, project, params)
        
        self.db_has_floor = True
        self.placeholder = '%s'
        
        self.url = params.get('url', None)
        if self.url is not None and self.url[0:13] != 'postgresql://':
            self.url = 'postgresql://' + self.url
        

    async def connect(self):
        if self.url is None:
            return await super().connect()
        
        try:
            conn = db.connect(self.url)
        except Exception as e:
            logging.error("PostgreSQL: %s: %s" % (self.url, str(e)))
            return await super().connect()
        if conn is None:
            return await super().connect()

        logging.info('PostgreSQL: DB connected: "%s"' % self.url)
        
        return SQLServer(conn)

    
    def _get_timediffsec_query(self, time_col, time_type, stop_sec, stop_tstamp):
        if time_type == 'unix':
            return f"{stop_sec} - {time_col}"
        else:
            return f"{stop_sec} - EXTRACT(epoch FROM {time_col})"
