# Created by Sanshiro Enomoto on 7 March 2025 #


import asyncio, re, logging, traceback
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
        self.placeholder_re = re.compile(r"%s")  # psycopg2 (%s) -> asyncpg ($1,$2,...)

        self.connection_error_reported = False

        
    def is_connected(self):
        return self.pool is not None
    
    
    async def terminate(self):
        if self.pool is not None:
            await self.pool.close()
            self.pool = None


    def _replace_placeholders(self, sql, params):
        if sql.count('%s') != len(params):
            raise ValueError('number of placeholders does not match number of params')
        def repl(match):
            repl.index += 1
            return f'${repl.index}'
        repl.index = 0
        return self.placeholder_re.sub(repl, sql)

    
    async def execute(self, sql, params=()):
        if self.pool is None:
            return AsyncPostgreSQLQueryResult()

        logging.debug(f'SQL Async Execute: {sql}; params={params}')
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(self._replace_placeholders(sql, params), *params)
                # asyncpg performs automatic commit
        except (
            # server crash (pool can be reused after server recovery)
            asyncpg.exceptions.PostgresConnectionError,
            asyncio.TimeoutError,
            OSError
        ) as e:
            logging.error(f'PostgreSQL Connection Error: {e}')
            return SQLQueryErrorResult(str(e))
        except Exception as e:
            if not self.connection_error_reported:
                logging.error(f'PostgreSQL Async Execute Error: {e}')
                self.connection_error_reported = True
            return SQLQueryErrorResult(str(e))

        if self.connection_error_reported:
            self.connection_error_reported = False
            logging.info(f'PostgreSQL: Reconnected')
            
        return AsyncPostgreSQLQueryResult()
        
            
        
    async def fetch(self, sql, params=()):
        if self.pool is None:
            return AsyncPostgreSQLQueryResult()
        
        logging.debug(f'PostgreSQL Async Fetch: {sql}; params={params}')
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(self._replace_placeholders(sql, params), *params)
        except (
            # server crash (pool can be reused after server recovery)
            asyncpg.exceptions.PostgresConnectionError,
            asyncio.TimeoutError,
            OSError
        ) as e:
            if not self.connection_error_reported:
                logging.error(f'PostgreSQL Connection Error: {e}')
                self.connection_error_reported = True
            return AsyncPostgreSQLQueryResult()
        except Exception as e:
            logging.error(f'PostgreSQL Async Fetch Error: {e}')
            return SQLQueryErrorResult(str(e))
    
        if self.connection_error_reported:
            self.connection_error_reported = False
            logging.info(f'PostgreSQL: Reconnected')
            
        return AsyncPostgreSQLQueryResult(rows)


    
class DataSource_PostgreSQL(DataSource_SQL):
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
            pool = await asyncpg.create_pool(self.url)
        except Exception as e:
            logging.error(f'AsyncPostgreSQL: {self.url}: {e}')
            pool = None
            
        if pool is None:
            return await super().connect()

        logging.info(f'AsyncPostgreSQL: DB connected: {self.url}')
        
        return AsyncPostgreSQLServer(pool)

    
    def _get_timediffsec_query(self, time_col, time_type, stop_sec, stop_tstamp):
        if time_type == 'unix':
            return f"{stop_sec} - {time_col}"
        else:
            return f"{stop_sec} - EXTRACT(epoch FROM {time_col})"
