# Created by Sanshiro Enomoto on 17 March 2025 #


import logging, traceback
from sd_dataschema import Schema
from sd_datasource_SQL import SQLBaseServer, SQLQueryResult, SQLQueryErrorResult, DataSource_SQL

import aiomysql


class AsyncMySQLQueryResult(SQLQueryResult):
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


    
class AsyncMySQLServer(SQLBaseServer):
    def __init__(self, pool):
        super().__init__()
        self.pool = pool

        
    def is_connected(self):
        return self.pool is not None
    
    
    async def terminate(self):
        if self.pool is not None:
            self.pool.close()
            await self.pool.wait_closed()
            self.pool = None

            
    async def execute(self, sql, *params):
        if self.pool is None:
            return AsyncMySQLQueryResult()

        logging.debug(f'SQL Async Execute: {sql}; params={params}')
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    await cursor.execute(sql, *params)
                    await conn.commit()
                except Exception as e:
                    logging.error(f'SQL Async Execute Error: {e}')
                    logging.error(traceback.format_exc())
            
        
    async def fetch(self, sql, *params):
        if self.pool is None:
            return AsyncMySQLQueryResult()
        
        logging.debug(f'SQL Async Fetch: {sql}; params={params}')
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                try:
                    await cursor.execute(sql, *params)
                    rows = await cursor.fetchall()
                    return AsyncMySQLQueryResult(rows)
                except Exception as e:
                    logging.error(f'SQL Fetch Error: {e}')
                    logging.error(traceback.format_exc())
                    return SQLQueryErrorResult(str(e))
            
    
    
class DataSource_AsyncMySQL(DataSource_SQL):
    def __init__(self, app, project, params):
        super().__init__(app, project, params)
        
        self.db_has_floor = True
        
        # Parse the MySQL-style URL into each parameter
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
            pool = await aiomysql.create_pool(
                host=self.host, port=self.port, user=self.user, password=self.password, db=self.database
            )
        except Exception as e:
            logging.error(f'AsyncMySQL: {self.url}: {e}')
            return None
        if pool is None:
            return None
        
        logging.info(f'AsyncMySQL: DB connected: {self.url}')
        
        return AsyncMySQLServer(pool)
