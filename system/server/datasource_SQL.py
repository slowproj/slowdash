# Created by Sanshiro Enomoto on 10 April 2023 #


import sys, os, logging, time, datetime
from datasource import DataSource, Schema


class SQLQueryResult:
    def __init__(self, cursor=None):
        self.cursor = cursor
        
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
            logging.error('SQL Query Error: %s' %(e))
            return SQLQueryResult()
            
        return SQLQueryResult(cursor)



    
class DataSource_SQL(DataSource):
    def __init__(self, project_config, config):
        super().__init__(project_config, config)
        self.server = None
        self.timeseries_table = None
        
        self.time_sep = 'T'
        self.db_has_floor = False
        
        self.configure(project_config, config)        
        self.channels_scanned = False


    # override this in DB implementation class
    def connect(self):
        if self.server is None:
            conn = None
            return SQLServer(conn)
    

    def configure(self, project_config, config):
        def load_schema(config, entrytype):
            schema_list = []
            entry_list = config.get(entrytype, [])
            for entry in entry_list if type(entry_list) is list else [ entry_list ]:
                schema_conf = entry.get('schema', None)
                if schema_conf is None:
                    logging.error('SQL: %s: table schema not specified' % entrytype)
                    continue
                tag_value_list = entry.get('tags', {}).get('list', [])
                schema = Schema(schema_conf, tag_value_list)
                schema.tag_value_sql = entry.get('tags', {}).get('sql', None)
                schema.is_for_ts = (entrytype == 'time_series')
                schema.is_for_obj = (entrytype == 'object')
                schema.suffix = entry.get('suffix', '')
                schema_list.append(schema)
            return schema_list

        self.ts_schemata = load_schema(config, 'time_series')
        self.obj_schemata = load_schema(config, 'object')
        self.objts_schemata = load_schema(config, 'object_time_series')

        self.views = {}
        views = config.get('view', [])
        if type(views) is not list:
            views = [views]
        for view in views:
            if not (('name' in view) and ('sql' in view)):
                logging.error('view needs "name" and "sql" fields: "%s"' % view)
                continue
            self.views[view['name']] = view['sql']
            

    def scan_channels(self):
        if self.channels_scanned:
            return
        self.channels_scanned = True
        
        if self.server is None:
            self.server = self.connect()
            
        for schema in self.ts_schemata + self.obj_schemata + self.objts_schemata:
            schema.initialize()
            if schema.table is None:
                logging.error('SQL: table name not specified')
                continue
            
            if schema.time is None:
                pass
            elif schema.time_type is None:
                logging.warn('SQL: time type not specified: "with timezone" is assumed')
                schema.time_type = 'aware'
            else:
                schema.time_type = schema.time_type.lower().replace(' ', '')
                if schema.time_type in ["withtimezone", "utc", "gmt"]:
                    schema.time_type = "aware"
                elif schema.time_type in ["withouttimezone", "local"]:
                    schema.time_type = "naive"
                elif schema.time_type == "unspecifiedutc":
                    schema.time_type = "unspecifiedutc"
                if schema.time_type not in [ 'unix', 'aware', 'naive', 'unspecifiedutc' ]:
                    logging.error('invalid time type: %s' % schema.time_type)
                    schema.timeseries_table = None

            if schema.tag is not None and len(schema.tag_values) == 0:
                if schema.tag_value_sql is None:
                    # TODO: this is inefficient. Modify not to go though all the DB entries.
                    schema.tag_value_sql = 'select distinct %s from %s' % (schema.tag, schema.table)
                try:
                    result = self.server.execute(schema.tag_value_sql).get_table()
                    schema.tag_values = [ row[0] for row in result ]
                except Exception as e:
                    logging.error('SQL Error: %s' % str(e))

            all_fields_have_types = True
            if not schema.is_for_ts:
                for k in range(len(schema.fields)):
                    if schema.field_types[k] is None:
                        all_fields_have_types = False
                        break

            if len(schema.fields) == 0 or not all_fields_have_types:
                sql = 'select * from %s limit 1' % schema.table
                try:
                    result = self.server.execute(sql)
                    columns = [ v for v in result.get_column_names() ]
                    table = result.get_table()
                    try:
                        record = table[0]
                    except:
                        record = [None] * len(columns)
                except Exception as e:
                    logging.error('SQL Error: %s' % str(e))
                fields = {}
                for k in range(len(columns)):
                    column = columns[k]
                    if column not in [ schema.time, schema.tag ] + schema.flags:
                        if schema.is_for_ts:
                            fields[column] = None
                        elif schema.tag is not None:
                            # will be determined later for each tag value
                            fields[column] = None
                        else:
                            datatype = Schema.identify_datatype(record[k])
                            fields[column] = datatype if datatype != 'timeseries' else None
                if len(schema.fields) == 0:
                    schema.fields = [ k for k in fields.keys() ]
                    schema.field_types = [ v for v in fields.values() ]
                else:
                    for k in range(len(schema.fields)):
                        if schema.field_types[k] is None:
                            schema.field_types[k] = fields.get(schema.fields[k], None)
                if len(schema.fields) == 1:
                    schema.default_field = schema.fields[0]
            
            if schema.tag is None:
                for k in range(len(schema.fields)):
                    ch = schema.fields[k]
                    if ch not in schema.channel_table:
                        schema.channel_table[ch] = { 'name': ch }
                    else:
                        schema.channel_table[ch]['name'] = ch
                    if schema.field_types[k] is not None:
                        schema.channel_table[ch]['type'] = schema.field_types[k]
            else:
                for tag_value in schema.tag_values:
                    for k in range(len(schema.fields)):
                        field = schema.fields[k]
                        if field == schema.default_field:
                            ch = tag_value
                        else:
                            ch = '%s%s%s' % (tag_value, Schema.tag_field_separator, field)
                        if ch not in schema.channel_table:
                            schema.channel_table[ch] = { 'name': ch }
                        else:
                            schema.channel_table[ch]['name'] = ch
                        if not schema.is_for_ts and schema.channel_table[ch].get('type', None) is None:
                            sql = 'select %s from %s where %s=="%s" limit 1' % (field, schema.table, schema.tag, tag_value)
                            try:
                                result = self.server.execute(sql)
                                value = result.get_table()[0][0]
                            except Exception as e:
                                logging.error('SQL Error: %s' % str(e))
                                continue
                            schema.channel_table[ch]['type'] = Schema.identify_datatype(value)

        
    def get_channels(self):
        self.channels_scanned = False  # forced scan; efficient for existing channels
        self.scan_channels()
            
        channels = []
        for schema in self.ts_schemata + self.obj_schemata + self.objts_schemata:
            for ch in schema.channel_table.values():
                ch['name'] = ch['name'] + schema.suffix
                channels.append(ch)
                
        channels += [ {'name': view, 'type': 'table'} for view in self.views ]

        return channels
        
    
    def get_timeseries(self, channels, length, to, resampling=None, reducer='last'):
        if not self.channels_scanned:
            self.scan_channels()
        
        result = {}
        for schema in self.ts_schemata:
            result.update(self.execute_query(
                schema, channels, length, to, resampling=resampling, reducer=reducer, lastonly=False
            ))
            
        if resampling is None:
            return result
            
        return self.resample(result, length, to, resampling, reducer)

    
    def get_object(self, channels, length, to):
        if self.server is None:
            self.server = self.connect()
        
        result = {}

        ### Key-Value and Time-Series of Objects ###
        
        for schema in self.obj_schemata + self.objts_schemata:
            if schema.tag is None:
                result.update(self.execute_query(
                    schema, channels, length, to, resampling=None, reducer=None, lastonly=True
                ))
            else:
                # to make use of "limit 1"
                for ch in channels:  
                    result.update(self.execute_query(
                        schema, [ch], length, to, resampling=None, reducer=None, lastonly=True
                    ))
            # retry if the value is null?
            
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


    
    def execute_query(self, schema, channels, length, to, resampling=None, reducer=None, lastonly=False):
        result = {}
        stop = int(to)
        start = int(stop - float(length))
        
        if self.server is None:
            self.server = self.connect()

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

        time_col, time_from, time_to = schema.get_query_times(start, stop)
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
        for row in self.server.execute(sql).get_table():
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
