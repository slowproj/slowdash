# Created by Sanshiro Enomoto on 10 April 2023 #


import sys, os, logging
from sd_datasource_SQL import SQLServer, SQLQueryResult, DataSource_SQL

import sqlalchemy as sqla


class SQLQueryResult_SQLAlchemy(SQLQueryResult):
    def __init__(self, cursor=None):
        super().__init__(cursor)
        
    def get_column_names(self):
        if self.cursor is None:
            return []
        return [ col for col in self.cursor.keys() ]



class SQLServer_SQLAlchemy(SQLServer):
    def execute(self, sql, commit=False):
        if self.conn is None:
            return SQLQueryResult()
        
        try:
            cursor = self.conn.execute(sqla.text(sql))
            if commit:
                self.conn.commit()
        except Exception as e:
            logging.error(e)
            return SQLQueryErrorResult(str(e))
            
        return SQLQueryResult_SQLAlchemy(cursor)


    
class DataSource_SQLAlchemy(DataSource_SQL):
    def __init__(self, app, project, params):
        super().__init__(app, project, params)

        self.db_has_floor = False
        
        self.url = params.get('url', None)
        if self.url is None:
            return
        
        db_type = self.url.split(':')[0]
        if db_type == 'sqlite':
            self.time_sep = ' '
            
            
    def connect(self):
        if self.url is None:
            return super().connect()

        try:
            engine = sqla.create_engine(self.url)
            conn = engine.connect()
        except Exception as e:
            logging.error(e)
            return super().connect()

        logging.info('SQLAlchemy: DB connected: "%s"' % self.url)
        
        return SQLServer_SQLAlchemy(conn)
