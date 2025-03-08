# Created by Sanshiro Enomoto on 10 April 2023 #


import sys, os, logging
from sd_datasource_SQL import SQLServer, SQLQueryResult, DataSource_SQL

import asyncpg


class AsyncSQLQueryResult(SQLQueryResult):
    def __init__(self, rows=None):
        self.rows = rows
        self.is_error = False

        
    def get_column_names(self):
        if self.rows:
            return self.rows[0].keys()
        else:
            return []

    
    def get_table(self):
        if self.rows is None:
            return []
        return [ [ v for k,v in dict(row) ] for row in self.rows ]


    
class AyncSQLServer(SQLServer):
    def __init__(self, pool):
        super().__init__(None)
        self.pool = pool

        
    async def terminate(self):
        if self.pool is not None:
            await self.pool.close()
            self.pool = None

            
    async def execute(self, sql, *params):
        if self.pool is None:
            return AsyncSQLQueryResult()

        logging.debug(f'Async SQL Execute: {sql}({params})')
        async with self.pool.actuire() as conn:
            await conn.execute(sql, *params)
            
        
    async def fetch(self, sql, *params):
        if self.pool is None:
            return AsyncSQLQueryResult()
        
        logging.debug(f'Async SQL Fetch: {sql}({params})')
        async with self.pool.actuire() as conn:
            rows = await conn.fetch(sql)
            
            try:
                cursor = conn.cursor()
                cursor.execute(sql)
            if commit:
                self.conn.commit()
        except Exception as e:
            logging.error('SQL Query Error: %s' % str(e))
            logging.error(traceback.format_exc())
            return SQLQueryErrorResult(str(e))
            
        return SQLQueryResult(cursor)


    
    
class DataSource_PostgreSQL(DataSource_SQL):
    def __init__(self, app, project, params):
        super().__init__(app, project, params)
        
        self.db_has_floor = True
        
        self.url = params.get('url', None)
        if self.url is not None and self.url[0:13] != 'postgresql://':
            self.url = 'postgresql://' + self.url
        

    async def connect(self):
        if self.url is None:
            return super().connect()
        
        try:
            pool = await asyncpg.create_pool(self.url)
        except Exception as e:
            logging.error("PostgreSQL: %s: %s" % (self.url, str(e)))
            return None
        if conn is None:
            return None

        logging.info('PostgreSQL: DB connected: "%s"' % self.url)
        
        return AsyncSQLServer(pool)
