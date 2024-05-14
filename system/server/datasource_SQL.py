# Created by Sanshiro Enomoto on 10 April 2023 #


import sys, os, time, datetime, logging, traceback
from datasource import DataSource, Schema
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
    def __init__(self, project_config, config):
        super().__init__(project_config, config)
        self.server = None
        self.time_sep = 'T'
        self.db_has_floor = False

        
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

    
    def _configure(self, project_config, config):
        super()._configure(project_config, config)
        
        self.views = {}
        views = config.get('view', [])
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
        result = self.server.execute(schema.tag_value_sql)
        if result.is_error:
            logging.error('SQL Error: %s: %s' % (result.error, schema.tag_value_sql))
            return None
        
        return [ row[0] for row in result.get_table() ]


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

                
    def _get_first_data_value(self, schema, tag_value, field):
        if schema.tag is not None:
            sql = "select %s from %s where %s='%s' limit 1" % (field, schema.table, schema.tag, tag_value)
        else:
            sql = "select %s from %s limit 1" % (field, schema.table)
        result = self.server.execute(sql)
        if result.is_error:
            logging.error('SQL Error: %s: %s' % (result.error, sql))
            return None
        try:
            value = result.get_table()[0][0]
        except Exception as e:
            return None

        
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
        
    
    def _execute_query(self, schema, channels, length, to, resampling=None, reducer=None, lastonly=False):
        result = {}
        stop = int(to)
        start = int(stop - float(length))
        
        if self.server is None:
            self.server = self._connect_with_retry()
        if self.server is None:
            return result

        if schema.time is None and not schema.is_for_obj:
            return result
            
        target_channels = []
        for name in channels:
            if not name.replace('.', '').replace('_', '').replace('-', '').replace(':', '').isalnum():
                logging.error('bad channel name: %s' % name)
            else:
                key = name[0:len(name)-len(schema.suffix)]
                if key in schema.channel_table:
                    target_channels.append(key)
        if len(target_channels) == 0:
            return result

        time_col, time_from, time_to = schema.get_query_times(start, stop, self.time_sep)
        if time_from is None or time_to is None:
            return result

        tag_values, fields, name_mapping = schema.get_query_tagvalues_fields(target_channels)
        if len(fields) < 1:
            return result

        if schema.tag is None:
            sql_select = 'SELECT %s' % ','.join([ time_col ] + fields)
        else:
            sql_select = 'SELECT %s' % ','.join([ time_col, schema.tag ] + fields)
        sql_from = 'FROM %s' % schema.table
        if schema.time is not None:
            sql_where_list = [ '%s>=%s' % (schema.time, time_from), '%s<%s' % (schema.time, time_to) ]
        else:
            sql_where_list = []
        if len(tag_values) > 0:
            sql_where_list += [ '%s in (%s)' % (schema.tag, ','.join([ "'%s'" % val for val in tag_values ])) ]
        sql_where = 'WHERE ' + ' AND '.join(sql_where_list)
        
        if schema.time is None:
            sql_orderby = ''
        elif lastonly:
            sql_orderby = 'ORDER BY %s DESC' % schema.time
            if len(channels) == 1 or schema.tag is None:
                sql_orderby = sql_orderby + ' limit 1'
        else:
            sql_orderby = 'ORDER BY %s ASC' % schema.time

        sql = None
        if schema.time is None or lastonly:
            pass
        elif resampling is None or resampling <= 0:
            pass
        else:
            if reducer in ['first', 'last'] and self.db_has_floor:
                sql_cte_bucket = ' '.join([
                    f"SELECT",
                    f"    floor(({stop}-extract(epoch from timestamp))/{resampling}) AS bucket, ",
                    f"    %s({schema.time}) AS picked_timestamp" % ("max" if reducer == 'last' else 'min'),
                    f"    %s" % ("" if schema.tag is None else f", {schema.tag}"),
                    f"{sql_from}",
                    f"{sql_where}",
                    f"GROUP BY ",
                    f"    bucket",
                    f"    %s" % ("" if schema.tag is None else f", {schema.tag}")
                ]);
                sql_cte_data = ' '.join([ sql_select, sql_from, sql_where ])
                sql = ' '.join([
                    f"WITH ",
                    f"    cte_bucket AS ({sql_cte_bucket}),",
                    f"    cte_data AS ({sql_cte_data})",
                    f"SELECT",
                    f"    {stop}-{resampling}*(bucket+0.5) AS {schema.time}, t.{schema.tag}, %s" % ','.join(fields),
                    f"FROM",
                    f"    cte_data AS t",
                    f"JOIN",
                    f"    cte_bucket AS b",
                    f"ON ",
                    f"    t.timestamp = b.picked_timestamp",
                    f"    %s" % ("" if schema.tag is None else f"AND t.{schema.tag} = b.{schema.tag}"),
                    f"{sql_orderby}"
                ])
            elif reducer in ['mean', 'sum', 'min', 'max'] and self.db_has_floor:  # "count" cannot be applied twice
                if reducer == 'mean':
                    agg_func = 'avg'
                else:
                    agg_func = reducer
                sql_cte_bucket = ' '.join([
                    f"SELECT",
                    f"    floor(({stop}-extract(epoch from timestamp))/{resampling}) AS bucket,",
                    f"    %s" % ("" if schema.tag is None else f"{schema.tag},"),
                    f"    %s" % ','.join([f"{agg_func}({field}) as {field}" for field in fields]),
                    f"{sql_from}",
                    f"{sql_where}",
                    f"GROUP BY ",
                    f"    bucket",
                    f"    %s" % (f", {schema.tag}" if schema.tag is not None else "")
                ]);
                sql = ' '.join([
                    f"WITH",
                    f"    cte_bucket AS ({sql_cte_bucket})",
                    f"SELECT",
                    f"    {stop}-{resampling}*(bucket+0.5) as {schema.time},",
                    f"    %s" % ("" if schema.tag is None else f"{schema.tag},"),
                    f"    %s" % ','.join(fields),
                    f"FROM",
                    f"    cte_bucket",
                    f"{sql_orderby}"
                ])
        if sql is None:
            sql = ' '.join([ sql_select, sql_from, sql_where, sql_orderby ])

        def add_result(channel, timestamp, value):
            if channel not in result:
                result[channel] = {
                    'start': start, 'length': int(length), 't': [], 'x': []
                }
            result[channel]['t'].append(int(1000*(timestamp-start))/1000.0)
            result[channel]['x'].append(value)
            
        remaining_channels = set(target_channels)
        query_result = self.server.execute(sql)
        if query_result.is_error:
            logging.error('SQL Query Error: %s: %s' % (query_result.error, sql))
        for row in query_result.get_table():
            if len(remaining_channels) <= 0:
                break
            
            timestamp = row[0]
            if type(timestamp) == str:
                timestamp = datetime.datetime.fromisoformat(timestamp)
            if type(timestamp).__name__ == 'datetime':
                if schema.time_type == 'unspecifiedutc':
                    timestamp = timestamp.replace(tzinfo=datetime.timezone.utc)
                timestamp = timestamp.timestamp()

            if schema.tag is None:
                # no tag: channel as field
                for k in range(len(fields)):
                    channel = fields[k]
                    if channel in remaining_channels:
                        if lastonly:
                            remaining_channels.remove(channel)
                        add_result(channel+schema.suffix, timestamp, row[1+k])
            else:
                # tag and fields
                for k in range(len(fields)):
                    channel = '%s%s%s' % (row[1], Schema.tag_field_separator, fields[k])
                    channel = name_mapping.get(channel, channel)
                    if channel in remaining_channels:
                        if lastonly:
                            remaining_channels.remove(channel)
                        add_result(channel+schema.suffix, timestamp, row[2+k])
                            
        return result
