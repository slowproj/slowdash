# Created by Sanshiro Enomoto on 10 April 2023 #
# Edited by Kou Oishi and Yuto Kageyama on 22 October 2024 #

import sys, os, logging
from datasource_SQL import SQLServer, DataSource_SQL

import MySQLdb as db
import re

class DataSource_MySQL(DataSource_SQL):
    def __init__(self, project_config, config):
        super().__init__(project_config, config)
        
        self.db_has_floor = True

        # Parse the PostgreSQL-style URL into each parameter
        self.url = config.get('url', None)
        if self.url is not None:
            if self.url[0:8] != 'mysql://':
                self.url = 'mysql://' + self.url

            # TODO: the port number should be omittable
            pattern = r"mysql://(\w+):(\w+)@(\w+):(\d+)/(\w+)"
            match = re.match(pattern, self.url)
            if match:
                self.user     = match.group(1)
                self.password = match.group(2)
                self.host     = match.group(3)
                self.port     = int(match.group(4))
                self.database = match.group(5)
            else:
                logging.error("Syntax error in the URL: %s" % (self.url))
            
    def connect(self):
        if self.url is None:
            return super().connect()
        
        try:
            conn = db.connect(host=self.host, port=self.port, user=self.user,
                              password=self.password, database=self.database,
                              autocommit=True)
        except Exception as e:
            logging.error("MySQL: %s: %s" % (self.url, str(e)))
            return super().connect()
        if conn is None:
            return super().connect()
        
        logging.info('MySQL: DB connected: "%s"' % self.url)
        
        return SQLServer(conn)

    # Override
    def _get_timestamp_in_query(self, var_name):
        # Should we care the case the variable is not a epoch (integer) value, e.g. TIMESTAMP?
        return var_name
