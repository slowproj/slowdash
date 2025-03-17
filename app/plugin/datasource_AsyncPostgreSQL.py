# Created by Sanshiro Enomoto on 7 March 2025 #


import logging, traceback
from sd_datasource_SQL import SQLBaseServer, SQLQueryResult, SQLQueryErrorResult, DataSource_SQL

import asyncpg


class AsyncPostgreSQLQueryResult(SQLQueryResult):
    def __init__(self, rows=None):
        super().__init__()
        self.rows = rows
        self.is_error = False

        
    def get_column_names(self):
        if self.rows:
            return self.rows[0].keys()
        else:
            return []

    
    def get_table(self):
        if self.rows:
            return [ [ v for v in dict(row).values() ] for row in self.rows ]
        else:
            return []


    
class AsyncPostgreSQLServer(SQLBaseServer):
    def __init__(self, pool):
        super().__init__()
        self.pool = pool

        
    def is_connected(self):
        return self.pool is not None
    
    
    async def terminate(self):
        if self.pool is not None:
            await self.pool.close()
            self.pool = None

            
    async def execute(self, sql, *params):
        if self.pool is None:
            return AsyncPostgreSQLQueryResult()

        logging.debug(f'SQL Async Execute: {sql}; params={params}')
        async with self.pool.acquire() as conn:
            try:
                await conn.execute(sql, *params)
                await conn.commit()
            except Exception as e:
                logging.error(f'SQL Async Execute Error: {e}')
                logging.error(traceback.format_exc())
            
        
    async def fetch(self, sql, *params):
        if self.pool is None:
            return AsyncPostgreSQLQueryResult()
        
        logging.debug(f'SQL Async Fetch: {sql}; params={params}')
        async with self.pool.acquire() as conn:
            try:
                rows = await conn.fetch(sql, *params)
                return AsyncPostgreSQLQueryResult(rows)
            except Exception as e:
                logging.error(f'SQL Async Fetch Error: {e}')
                logging.error(traceback.format_exc())
                return SQLQueryErrorResult(str(e))
            
    
    
class DataSource_AsyncPostgreSQL(DataSource_SQL):
    def __init__(self, app, project, params):
        super().__init__(app, project, params)
        
        self.db_has_floor = True
        
        self.url = params.get('url', None)
        if self.url is not None and self.url[0:13] != 'postgresql://':
            self.url = 'postgresql://' + self.url
        

    async def connect(self):
        if self.url is None:
            return await super().connect()
        
        try:
            pool = await asyncpg.create_pool(self.url)
        except Exception as e:
            logging.error(f'AsyncPostgreSQL: {self.url}: {e}')
            return None
        if pool is None:
            return None

        logging.info(f'AsyncPostgreSQL: DB connected: {self.url}')
        
        return AsyncPostgreSQLServer(pool)
