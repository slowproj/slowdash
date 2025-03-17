# Created by Sanshiro Enomoto on 10 April 2023 #
# Edited by Kou Oishi and Yuto Kageyama on 22 October 2024 #

import sys, os, logging
from sd_datasource_SQL import SQLServer, DataSource_SQL

import MySQLdb as db
import re

class DataSource_MySQL(DataSource_SQL):
    def __init__(self, app, project, params):
        super().__init__(app, project, params)
        
        self.db_has_floor = True

        # Parse the PostgreSQL-style URL into each parameter
        self.url = params.get('url', None)
        if self.url is not None:
            if self.url[0:8] != 'mysql://':
                self.url = 'mysql://' + self.url

            # TODO: the port number should be omittable
            pattern = r"mysql://([\w.-]+):(.+?)@([\w.-]+):(\d+)/([\w.-]+)"
            match = re.match(pattern, self.url)
            if match:
                self.user     = match.group(1)
                self.password = match.group(2)
                self.host     = match.group(3)
                self.port     = int(match.group(4))
                self.database = match.group(5)
            else:
                logging.error("Syntax error in the URL: %s" % (self.url))

                
    async def connect(self):
        if self.url is None:
            return await super().connect()
        
        try:
            conn = db.connect(host=self.host, port=self.port, user=self.user,
                              password=self.password, database=self.database,
                              autocommit=True)
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
        
