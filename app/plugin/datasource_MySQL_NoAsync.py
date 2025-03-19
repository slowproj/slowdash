# Created by Sanshiro Enomoto on 10 April 2023 #
# Edited by Kou Oishi and Yuto Kageyama on 22 October 2024 #
# Edited by Sanshiro Enomoto on 18 March 2025 #

import sys, logging
from sd_dataschema import Schema
from sd_datasource_SQL import SQLServer, DataSource_SQL

# either below should work
#import pymysql as mysql    # this requires "pip install mypysql cryptography"
import mysql.connector as mysql


class DataSource_MySQL_NoAsync(DataSource_SQL):
    def __init__(self, app, project, params):
        super().__init__(app, project, params)
        
        self.db_has_floor = True

        # Parse the PostgreSQL-style URL into each parameter
        self.url = params.get('url', None)
        if self.url is not None:
            if self.url[0:8] != 'mysql://':
                self.url = 'mysql://' + self.url

            dburl = Schema.parse_dburl(self.url)
            self.host = params.get('host', dburl.get('host', 'localhost'))
            self.port = int(params.get('port', dburl.get('port', '3306')))
            self.user = params.get('user', dburl.get('user', None))
            self.password = params.get('password', dburl.get('password', None))
            self.database = params.get('db', dburl.get('db', None))

                
    async def connect(self):
        if self.url is None:
            return await super().connect()
        
        try:
            conn = mysql.connect(host=self.host, port=self.port, user=self.user,
                              password=self.password, database=self.database)
        except Exception as e:
            logging.error("MySQL: %s: %s" % (self.url, str(e)))
            return await super().connect()
        if conn is None:
            return await super().connect()
        
        logging.info('MySQL: DB connected: "%s"' % self.url)
        
        return SQLServer(conn)

    
    # Override
    def _get_timediffsec_query(self, time_col, time_type, stop_sec, stop_tstamp):
        if time_type == 'unix':
            return f"{stop_sec} - {time_col}"
        else:
            return f"TIME_TO_SEC( TIMEDIFF({stop_tstamp}, {time_col}) )"
        
