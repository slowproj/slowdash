# Created by Sanshiro Enomoto on 10 April 2023 #


import sys, os, asyncio, time, datetime, logging, traceback
from sd_datasource import DataSource
from sd_dataschema import Schema
from sd_datasource_TableStore import DataSource_TableStore


class SQLQueryResult:
    def __init__(self, cursor=None):
        self.cursor = cursor
        self.is_error = False

        
    def __del__(self):
        if self.cursor is not None:
            self.cursor.close()

            
    def get_column_names(self):
        if self.cursor:
            return [ col[0] for col in self.cursor.description ]
        else:
            return []

    
    def get_table(self):
        if self.cursor:
            return self.cursor.fetchall()
        else:
            return []

    

class SQLQueryErrorResult(SQLQueryResult):
    def __init__(self, error_message):
        super().__init__(None)
        self.is_error = True
        self.error = error_message

        

class SQLBaseServer:
    def __init__(self):
        pass

    
    def is_connected(self):
        return False
    
    
    async def terminate(self):
        pass
    

    async def execute(self, sql, params=()):
        return SQLQueryResult()
            
        
    async def fetch(self, sql, params=()):
        return SQLQueryResult()

    
    
class SQLServer(SQLBaseServer):
    def __init__(self, conn):
        super().__init__()
        self.conn = conn

        
    def is_connected(self):
        return self.conn is not None
    
    
    async def terminate(self):
        if self.conn is not None:
            self.conn.close()
            self.conn = None

            
    async def execute(self, sql, params=()):
        if self.conn is None:
            return SQLQueryResult()

        logging.debug(f'SQL Execute: {sql}; params={params}')
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, params)
            self.conn.commit()
        except Exception as e:
            logging.error(f'SQL Fetch Error: {e}')
            logging.error(traceback.format_exc())
            return SQLQueryErrorResult(str(e))
            
        return SQLQueryResult(cursor)
            
        
    async def fetch(self, sql, params=()):
        if self.conn is None:
            return SQLQueryResult()

        logging.debug(f'SQL Fetch: {sql}; params={params}')
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, params)
        except Exception as e:
            logging.error(f'SQL Fetch Error: {e}')
            logging.error(traceback.format_exc())
            return SQLQueryErrorResult(str(e))
            
        return SQLQueryResult(cursor)


    
class DataSource_SQL(DataSource_TableStore):
    def __init__(self, app, project, params):
        self.server = None
        self.time_sep = 'T'
        self.placeholder = '?'
        self.db_has_floor = False
        super().__init__(app, project, params)


    async def aio_finalize(self):
        if self.server is not None:
            try:
                await self.server.terminate()
            except Exception as e:
                logging.warning(f'SQL termination error: {e}')

        
    # override this in DB implementation class
    async def connect(self):
        if self.server is not None:
            return self.server
        return SQLBaseServer()
    

    async def aio_get_channels(self):
        self.channels_scanned = False  # forced scan; efficient for existing channels
        channels = await super().aio_get_channels()
        channels += [ {'name': view, 'type': 'table'} for view in self.views ]

        return channels
        
    
    async def aio_get_timeseries(self, channels, length, to, resampling=None, reducer='last', filler='fillna', envelope=0):
        if self.server is None:
            self.server = await self._connect_with_retry()
        if self.server is None:
            return {}
        
        return await super().aio_get_timeseries(channels, length, to, resampling, reducer, filler, envelope)

        
    async def aio_get_object(self, channels, length, to):
        if self.server is None:
            self.server = await self._connect_with_retry()
        if self.server is None:
            return {}
        
        result = await super().aio_get_object(channels, length, to)
        
        ### VIEW ###
        start = to - length
        start_datetime_naive = datetime.datetime.fromtimestamp(start)
        start_datetime_utc = start_datetime_naive.astimezone(datetime.timezone.utc)
        to_datetime_naive = datetime.datetime.fromtimestamp(to)
        to_datetime_utc = to_datetime_naive.astimezone(datetime.timezone.utc)
        for ch in channels:
            if ch not in self.views:
                continue
            sql = self.views[ch]
            sql = sql.replace('${FROM_UNIXTIME}', '%d' % start)
            sql = sql.replace('${FROM_DATETIME}', start_datetime_utc.isoformat(sep=self.time_sep))
            sql = sql.replace('${FROM_DATETIME_NAIVE}', start_datetime_naive.isoformat(sep=self.time_sep))
            sql = sql.replace('${FROM_DATETIME_UTC}', start_datetime_utc.isoformat(sep=self.time_sep))
            sql = sql.replace('${TO_UNIXTIME}', '%d' % to)
            sql = sql.replace('${TO_DATETIME}', to_datetime_utc.isoformat(sep=self.time_sep))
            sql = sql.replace('${TO_DATETIME_NAIVE}', to_datetime_naive.isoformat(sep=self.time_sep))
            sql = sql.replace('${TO_DATETIME_UTC}', to_datetime_utc.isoformat(sep=self.time_sep))

            try:
                query_result = await self.server.fetch(sql)
            except Exception as e:
                logging.error('SQL Query Error: %s: %s' % (str(e), sql))
                continue
            if query_result.is_error:
                logging.error('SQL Query Error: %s: %s' % (query_result.error, sql))
                continue

            table = {
                'columns': [k for k in query_result.get_column_names()],
                'table': []
            }
            for row in query_result.get_table():
                table['table'].append([v for v in row])

            result[ch] = {
                'start': start, 'length': length,
                't': to,
                'x': table
            }
        
        return result

    
    def _configure(self, params):
        super()._configure(params)
        
        self.views = {}
        views = params.get('view', [])
        if type(views) is not list:
            views = [views]
        for view in views:
            if not (('name' in view) and ('sql' in view)):
                logging.error('view needs "name" and "sql" fields: "%s"' % view)
                continue
            self.views[view['name']] = view['sql']
            

    async def _scan_channels(self):
        if self.server is None:
            self.server = await self._connect_with_retry()
        if self.server is None:
            return
            
        await super()._scan_channels()

        
    async def _get_tag_values_from_data(self, schema):
        if schema.tag_value_sql is None:
            # TODO: this is inefficient. Modify not to go though all the DB entries.
            schema.tag_value_sql = f"SELECT DISTINCT {schema.tag} FROM {schema.table}"

        try:
            start_time = time.time()
            result = await self.server.fetch(schema.tag_value_sql)
            lapse = time.time() - start_time
        except Exception as e:
            logging.error(f'SQL Error: {e}')   # most likely the table does not exist (yet)
            return []
            
        if lapse > 10:
            logging.warning(f'Full scan of a SQL table ({schema.table}) was performed to obtain a list of available channels. It took {int(lapse)} seconds.')
            logging.warning('  This full-scan can be avoided by either:')
            logging.warning('    - manually list the channels, in "data_source/time_series/tags/list" as an array, or')
            logging.warning('    - provide a SQL that returns the list, in "data_source/time_series/tags/sql" as a string')
        if result.is_error:
            logging.error('SQL Error: %s: %s' % (result.error, schema.tag_value_sql))
            return None
        
        return sorted([ row[0] for row in result.get_table() ])


    async def _get_first_data_row(self, schema):
        sql = f"SELECT * FROM {schema.table} LIMIT 1"
        try:
            result = await self.server.fetch(sql)
        except Exception as e:
            logging.error('SQL Error: %s: %s' % (str(e), sql))
            return None, []
        if result.is_error:
            #logging.error('SQL Error: %s: %s' % (result.error, sql))
            return None, []
        columns = [ v for v in result.get_column_names() ]
        table = result.get_table()
        try:
            record = table[0]
        except:
            record = [None] * len(columns)

        return columns, record

                
    async def _get_first_data_value(self, table_name, tag_name, tag_value, field):
        if tag_name is not None:
            sql = f"SELECT {field} FROM {table_name} WHERE {tag_name}={self.placeholder} LIMIT 1"
            params = (tag_value,)
        else:
            sql = f"SELECT {field} FROM {table_name} LIMIT 1"
            params = ()
        try:
            result = await self.server.fetch(sql, params)
        except Exception as e:
            logging.error('SQL Error: %s: %s' % (str(e), sql))
            return None
        if result.is_error:
            logging.error('SQL Error: %s: %s' % (result.error, sql))
            return None
        try:
            value = result.get_table()[0][0]
        except Exception as e:
            logging.error('SQL Error: %s: %s' % (str(e), sql))
            return None

        return value

        
    async def _connect_with_retry(self, repeat=12, interval=5):
        if self.server is not None:
            return self.server
        
        for i in range(repeat):
            try:
                server = await self.connect()
            except Exception as e:
                logging.info('Unable to connect to SQLDB: %s' % str(e))
                server = None
            if (server is None) or (not server.is_connected()):
                logging.info(f'retrying in 5 sec... ({i+1}/{repeat})')
                await asyncio.sleep(interval)
            else:
                return server
        else:
            logging.error('Unable to connect to SQLDB')
            if server is None:
                logging.error(traceback.format_exc())
            return SQLBaseServer()

        
    # The DB-specific syntax to get a time difference between time_col and (stop_sec | stop_tstamp) 
    # Override this if needed
    def _get_timediffsec_query(self, time_col, time_type, stop_sec, stop_tstamp):
        if time_type == 'unix':
            return f"{stop_sec} - {time_col}"
        else:
            return None

    
    async def _execute_query(self, table_name, time_col, time_type, time_from, time_to, tag_col, tag_values, fields, resampling=None, reducer=None, stop=None, lastonly=False, use_server_resampling=True):
        if self.server is None:
            self.server = await self._connect_with_retry()
        if self.server is None:
            return [], []

        sql = None
        params = []
        
        if time_col is None:
            time_field = '%.3f' % float(time.time())
        else:
            time_field = time_col
        if tag_col is None:
            sql_select = f"SELECT {','.join([ time_field ] + fields)}"
        else:
            sql_select = f"SELECT {','.join([ time_field, tag_col ] + fields)}"
        sql_from = f"FROM {table_name}"
        if time_col is not None:
            sql_where_list = [ f"{time_col}>={time_from}", f"{time_col}<{time_to}" ]
        else:
            sql_where_list = []
        params_where = []
        if len(tag_values) > 0:
            sql_where_list += [ f"{tag_col} IN ({','.join([self.placeholder]*len(tag_values))})" ]
            params_where.extend(tag_values)
        sql_where = 'WHERE ' + ' AND '.join(sql_where_list) if len(sql_where_list) > 0 else ''
        
        if time_col is None:
            sql_orderby = ''
        elif lastonly:
            sql_orderby = f"ORDER BY {time_col} DESC"
            if (tag_col is None) or (len(tag_values) == 1):
                sql_orderby += ' limit 1'
        else:
            sql_orderby = f"ORDER BY {time_col} ASC"

        if time_col is None or lastonly:
            pass
        elif resampling is None or resampling <= 0:
            pass
        elif not self.db_has_floor:
            pass  # no server-side resampling -> resampling in Python        
        else:
            # The syntax to get the time difference may depend on the SQL type
            tdiff_query = self._get_timediffsec_query(time_col, time_type, stop, time_to)
            if not use_server_resampling:
                pass  # no server-side resampling -> resampling in Python
            
            elif tdiff_query is None:
                pass  # no server-side resampling -> resampling in Python
            
            elif reducer in ['first', 'last']:
                sql_cte_bucket = ' '.join([
                    f"SELECT",
                    f"    FLOOR(({tdiff_query})/{resampling}) AS bucket, ",
                    f"    %s({time_col}) AS picked_timestamp" % ("max" if reducer == 'last' else 'min'),
                    f"    %s" % ("" if tag_col is None else f", {tag_col}"),
                    f"{sql_from}",
                    f"{sql_where}",
                    f"GROUP BY ",
                    f"    bucket",
                    f"    %s" % ("" if tag_col is None else f", {tag_col}")
                ]);
                sql_cte_data = ' '.join([ sql_select, sql_from, sql_where ])
                sql = ' '.join([
                    f"WITH ",
                    f"    cte_bucket AS ({sql_cte_bucket}),",
                    f"    cte_data AS ({sql_cte_data})",
                    f"SELECT",
                    f"    {stop}-{resampling}*(bucket+0.5) AS {time_col}, t.{tag_col}, {','.join(fields)}",
                    f"FROM",
                    f"    cte_data AS t",
                    f"JOIN",
                    f"    cte_bucket AS b",
                    f"ON ",
                    f"    t.{time_col} = b.picked_timestamp",
                    f"    %s" % ("" if tag_col is None else f"AND t.{tag_col} = b.{tag_col}"),
                    f"{sql_orderby}"
                ])
                params.extend(params_where)
                params.extend(params_where)
                
            elif reducer in ['mean', 'sum', 'min', 'max']:  # "count" cannot be applied twice
                if reducer == 'mean':
                    agg_func = 'avg'
                else:
                    agg_func = reducer
                sql_cte_bucket = ' '.join([
                    f"SELECT",
                    f"    FLOOR(({tdiff_query})/{resampling}) AS bucket,",
                    f"    %s" % ("" if tag_col is None else f"{tag_col},"),
                    f"    %s" % ','.join([f"{agg_func}({field}) as {field}" for field in fields]),
                    f"{sql_from}",
                    f"{sql_where}",
                    f"GROUP BY ",
                    f"    bucket",
                    f"    %s" % (f", {tag_col}" if tag_col is not None else "")
                ]);
                sql = ' '.join([
                    f"WITH",
                    f"    cte_bucket AS ({sql_cte_bucket})",
                    f"SELECT",
                    f"    {stop}-{resampling}*(bucket+0.5) as {time_col},",
                    f"    %s" % ("" if tag_col is None else f"{tag_col},"),
                    f"    {','.join(fields)}",
                    f"FROM",
                    f"    cte_bucket",
                    f"{sql_orderby}"
                ])
                params.extend(params_where)
                
        if sql is None:
            sql = ' '.join([ sql_select, sql_from, sql_where, sql_orderby ])
            params.extend(params_where)

        logging.debug(f'SQL: {sql} , params:{params}');
        query_result = await self.server.fetch(sql, params)
        if query_result.is_error:
            logging.error('SQL Query Error: %s: %s (params=%s)' % (query_result.error, sql, str(params)))
            return [], []

        return query_result.get_column_names(), query_result.get_table()
