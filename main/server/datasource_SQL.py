# Created by Sanshiro Enomoto on 10 April 2023 #


import sys, os, time, datetime, logging, traceback
from datasource import DataSource
from dataschema import Schema
from datasource_TableStore import DataSource_TableStore


class SQLQueryResult:
    def __init__(self, cursor=None):
        self.cursor = cursor
        self.is_error = False
        
    def __del__(self):
        if self.cursor is not None:
            self.cursor.close()
        
    def get_column_names(self):
        if self.cursor is None:
            return []
        return [ col[0] for col in self.cursor.description ]

    def get_table(self):
        if self.cursor is None:
            return []
        return self.cursor.fetchall()

    

class SQLQueryErrorResult(SQLQueryResult):
    def __init__(self, error_message):
        super().__init__(None)
        self.is_error = True
        self.error = error_message

        

class SQLServer():
    def __init__(self, conn):
        self.conn = conn

        
    def __del__(self):
        if self.conn is not None:
            self.conn.close()

        
    def execute(self, sql, commit=False):
        if self.conn is None:
            return SQLQueryResult()

        logging.debug("SQL Execute: %s" % sql)
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql)
            if commit:
                self.conn.commit()
        except Exception as e:
            logging.error('SQL Query Error: %s' % str(e))
            logging.error(traceback.format_exc())
            return SQLQueryErrorResult(str(e))
            
        return SQLQueryResult(cursor)


    
class DataSource_SQL(DataSource_TableStore):
    def __init__(self, app, project, params):
        self.server = None
        self.time_sep = 'T'
        self.db_has_floor = False
        super().__init__(app, project, params)

        
    # override this in DB implementation class
    def connect(self):
        if self.server is not None:
            return self.server
        return SQLServer(None)
    

    def get_channels(self):
        self.channels_scanned = False  # forced scan; efficient for existing channels
        channels = super().get_channels()
        channels += [ {'name': view, 'type': 'table'} for view in self.views ]

        return channels
        
    
    def get_timeseries(self, channels, length, to, resampling=None, reducer='last'):
        if self.server is None:
            self.server = self._connect_with_retry()
        if self.server is None:
            return {}
        
        return super().get_timeseries(channels, length, to, resampling, reducer)

        
    def get_object(self, channels, length, to):
        if self.server is None:
            self.server = self._connect_with_retry()
        if self.server is None:
            return {}
        
        result = super().get_object(channels, length, to)
        
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
            
            query_result = self.server.execute(sql)
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
            

    def _scan_channels(self):
        if self.server is None:
            self.server = self._connect_with_retry()
        if self.server is None:
            return
            
        super()._scan_channels()

        
    def _get_tag_values_from_data(self, schema):
        if schema.tag_value_sql is None:
            # TODO: this is inefficient. Modify not to go though all the DB entries.
            schema.tag_value_sql = 'select distinct %s from %s' % (schema.tag, schema.table)
            
        start_time = time.time()
        result = self.server.execute(schema.tag_value_sql)
        lapse = time.time() - start_time
        if lapse > 10:
            logging.warning(f'Full scan of a SQL table ({schema.table}) was performed to obtain a list of available channels. It took {int(lapse)} seconds.')
            logging.warning('  This full-scan can be avoided by either:')
            logging.warning('    - manually list the channels, in "data_source/time_series/tags/list" as an array, or')
            logging.warning('    - provide a SQL that returns the list, in "data_source/time_series/tags/sql" as a string')
        if result.is_error:
            logging.error('SQL Error: %s: %s' % (result.error, schema.tag_value_sql))
            return None
        
        return sorted([ row[0] for row in result.get_table() ])


    def _get_first_data_row(self, schema):
        sql = 'select * from %s limit 1' % schema.table
        result = self.server.execute(sql)
        if result.is_error:
            logging.error('SQL Error: %s: %s' % (result.error, sql))
            return None, []
        columns = [ v for v in result.get_column_names() ]
        table = result.get_table()
        try:
            record = table[0]
        except:
            record = [None] * len(columns)

        return columns, record

                
    def _get_first_data_value(self, table_name, tag_name, tag_value, field):
        if tag_name is not None:
            sql = "select %s from %s where %s='%s' limit 1" % (field, table_name, tag_name, tag_value)
        else:
            sql = "select %s from %s limit 1" % (field, table_name)
        result = self.server.execute(sql)
        if result.is_error:
            logging.error('SQL Error: %s: %s' % (result.error, sql))
            return None
        try:
            value = result.get_table()[0][0]
        except Exception as e:
            logging.error('SQL Error: %s: %s' % (str(e), sql))
            return None

        return value

        
    def _connect_with_retry(self, repeat=12, interval=5):
        if self.server is not None:
            return self.server
        
        for i in range(repeat):
            try:
                server = self.connect()
            except Exception as e:
                logging.info('Unable to connect to SQLDB: %s' % str(e))
                server = None
            if server is None or server.conn is None:
                logging.info('retrying in 5 sec...')
                time.sleep(interval)
            else:
                return server
        else:
            logging.error('Unable to connect to SQLDB')
            logging.error(traceback.format_exc())
            return SQLServer(None)

    # The DB-specific syntax to get a time difference between time_col and (stop_sec | stop_tstamp) 
    # Override this if needed
    def _get_timediffsec_query(self, time_col, time_type, stop_sec, stop_tstamp):
        # Probably this is a common way in PostgreSQL?
        # Doesn't it depend on the time_type? what if {time_col} is already a unix/int?
        return f"{stop_sec} - extract(epoch from {time_col})"
    
    def _execute_query(self, table_name, time_col, time_type, time_from, time_to, tag_col, tag_values, fields, resampling=None, reducer=None, stop=None, lastonly=False):
        if self.server is None:
            self.server = self._connect_with_retry()
        if self.server is None:
            return [], []

        if time_col is None:
            time_field = '%.3f' % float(time.time())
        else:
            time_field = time_col
        if tag_col is None:
            sql_select = 'SELECT %s' % ','.join([ time_field ] + fields)
        else:
            sql_select = 'SELECT %s' % ','.join([ time_field, tag_col ] + fields)
        sql_from = 'FROM %s' % table_name
        if time_col is not None:
            sql_where_list = [ '%s>=%s' % (time_col, time_from), '%s<%s' % (time_col, time_to) ]
        else:
            sql_where_list = []
        if len(tag_values) > 0:
            sql_where_list += [ '%s in (%s)' % (tag_col, ','.join([ "'%s'" % val for val in tag_values ])) ]
        sql_where = 'WHERE ' + ' AND '.join(sql_where_list)
        
        if time_col is None:
            sql_orderby = ''
        elif lastonly:
            sql_orderby = 'ORDER BY %s DESC' % time_col
            if (tag_col is None) or (len(tag_values) == 1):
                sql_orderby += ' limit 1'
        else:
            sql_orderby = 'ORDER BY %s ASC' % time_col

        sql = None
        if time_col is None or lastonly:
            pass
        elif resampling is None or resampling <= 0:
            pass
        else:
            # The syntax to get the time difference may depend on the SQL type
            tdiff_query = self._get_timediffsec_query(time_col, time_type, stop, time_to)
            
            if reducer in ['first', 'last'] and self.db_has_floor:
                sql_cte_bucket = ' '.join([
                    f"SELECT",
                    f"    floor(({tdiff_query})/{resampling}) AS bucket, ",
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
                    f"    {stop}-{resampling}*(bucket+0.5) AS {time_col}, t.{tag_col}, %s" % ','.join(fields),
                    f"FROM",
                    f"    cte_data AS t",
                    f"JOIN",
                    f"    cte_bucket AS b",
                    f"ON ",
                    f"    t.{time_col} = b.picked_timestamp",
                    f"    %s" % ("" if tag_col is None else f"AND t.{tag_col} = b.{tag_col}"),
                    f"{sql_orderby}"
                ])
            elif reducer in ['mean', 'sum', 'min', 'max'] and self.db_has_floor:  # "count" cannot be applied twice
                if reducer == 'mean':
                    agg_func = 'avg'
                else:
                    agg_func = reducer
                sql_cte_bucket = ' '.join([
                    f"SELECT",
                    f"    floor(({tdiff_query})/{resampling}) AS bucket,",
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
                    f"    %s" % ','.join(fields),
                    f"FROM",
                    f"    cte_bucket",
                    f"{sql_orderby}"
                ])
        if sql is None:
            sql = ' '.join([ sql_select, sql_from, sql_where, sql_orderby ])

        query_result = self.server.execute(sql)
        if query_result.is_error:
            logging.error('SQL Query Error: %s: %s' % (query_result.error, sql))
            return [], []

        return query_result.get_column_names(), query_result.get_table()
