# Created by Sanshiro Enomoto on 10 April 2023 #


import sys, os, datetime, logging
from sd_dataschema import Schema
from sd_datasource import DataSource


class DataSource_TableStore(DataSource):
    def __init__(self, app, project, params):
        super().__init__(app, project, params)
        self.timeseries_table = None
        
        self._configure(params)        
        self.channels_scanned = False
        
        
    # override this
    async def _get_tag_values_from_data(self, schema):
        return None

    
    # override this
    async def _get_first_data_row(self, schema):
        columns, record = None, []
        return columns, record

    
    # override this
    async def _get_first_data_value(self, table_name, tag_name, tag_value, field):
        return None

        
    # override this
    async def _execute_query(self, table_name, time_col, time_type, time_from, time_to, tag, tag_values, fields, resampling=None, reducer=None, stop=None, lastonly=False):
        columns, table = [], []
        return columns, table

        
    async def aio_get_channels(self):
        await self._scan_channels()
            
        channels = []
        for schema in self.ts_schemata + self.obj_schemata + self.objts_schemata:
            for ch in schema.channel_table.values():
                ch_str = str(ch['name'])
                if 'type' in ch:
                    channels.append({ 'name': ch_str + schema.suffix, 'type': ch['type'] })
                else:
                    channels.append({ 'name': ch_str + schema.suffix })
                
        return channels
        
    
    async def aio_get_timeseries(self, channels, length, to, resampling=None, reducer='last'):
        if not self.channels_scanned:
            await self._scan_channels()
        
        result = {}
        for schema in self.ts_schemata:
            result.update(await self._get_query_result(
                schema, channels, length, to, resampling=resampling, reducer=reducer, lastonly=False
            ))
            
        if resampling is None:
            return result
            
        return self.resample(result, length, to, resampling, reducer)

    
    async def aio_get_object(self, channels, length, to):
        result = {}
        for schema in self.obj_schemata + self.objts_schemata:
            if schema.tag is None:
                result.update(await self._get_query_result(
                    schema, channels, length, to, resampling=None, reducer=None, lastonly=True
                ))
            else:
                # to make use of "limit 1"
                for ch in channels:  
                    result.update(await self._get_query_result(
                        schema, [ch], length, to, resampling=None, reducer=None, lastonly=True
                    ))
            # retry if the value is null?
            
        return result

    
    def public_config(self):
        return {
            'schemata': {
                'time_series': [ str(s) for s in self.ts_schemata ],
                'object': [ str(s) for s in self.obj_schemata ],
                'object_time_series': [ str(s) for s in self.objts_schemata ],
            },
        }
        
    def _configure(self, params):
        def load_schema(params, entrytype):
            schema_list = []
            entry_list = params.get(entrytype, [])
            for entry in entry_list if type(entry_list) is list else [ entry_list ]:
                schema_conf = entry.get('schema', None)
                if schema_conf is None:
                    logging.error('%s: table schema not specified' % entrytype)
                    continue
                tag_value_list = entry.get('tags', {}).get('list', [])
                schema = Schema(schema_conf, tag_value_list)
                schema.tag_value_sql = entry.get('tags', {}).get('sql', None)
                schema.is_for_ts = (entrytype == 'time_series')
                schema.is_for_obj = (entrytype == 'object')
                schema.suffix = entry.get('suffix', '')
                schema_list.append(schema)
            return schema_list

        self.ts_schemata = load_schema(params, 'time_series')
        self.obj_schemata = load_schema(params, 'object')
        self.objts_schemata = load_schema(params, 'object_time_series')

        
    async def _scan_channels(self):
        if self.channels_scanned:
            return
        self.channels_scanned = True
        
        for schema in self.ts_schemata + self.obj_schemata + self.objts_schemata:
            schema.initialize()
            if schema.table is None:
                logging.error('schema: table name not specified')
                continue
            
            # time type #
            if schema.time is None:
                pass
            elif schema.time_type is None:
                logging.warning('schema: time type not specified: "with timezone" is assumed')
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

            # scan for tag values #
            if schema.tag is not None and len(schema.tag_values) == 0:
                tag_values = await self._get_tag_values_from_data(schema)
                if tag_values is None: # error
                    continue
                else:
                    schema.tag_values = tag_values

            # scan for fields #
            all_fields_have_types = True
            if not schema.is_for_ts:
                for k in range(len(schema.fields)):
                    if schema.field_types[k] is None:
                        all_fields_have_types = False
                        break
            if len(schema.fields) == 0 or not all_fields_have_types:
                columns, record = await self._get_first_data_row(schema)
                if columns is None:
                    self.channels_scanned = False  # maybe the table is not created yet. Try again later
                    continue
                    
                fields = {}
                for k in range(len(columns)):
                    column = columns[k]
                    if column not in [ schema.time, schema.tag ] + schema.flags:
                        if False and schema.is_for_ts:  # "False" to determine the field type anyway
                            fields[column] = None
                        elif schema.tag is not None:
                            # will be determined later for each tag value
                            fields[column] = None
                        else:
                            fields[column] = Schema.identify_datatype(record[k])
                if len(schema.fields) == 0:
                    schema.fields = [ k for k in fields.keys() ]
                    schema.field_types = [ v for v in fields.values() ]
                else:
                    for k in range(len(schema.fields)):
                        if schema.field_types[k] is None:
                            schema.field_types[k] = fields.get(schema.fields[k], None)
                if len(schema.fields) == 1:
                    schema.default_field = schema.fields[0]

            # channel names #
            if schema.tag is None:
                # fields only -> field names are channel names
                for k in range(len(schema.fields)):
                    schema.add_channel(schema.fields[k], schema.field_types[k])
            else:
                # tags and fields -> combine tag_values and fields
                for tag_value in schema.tag_values:
                    for k in range(len(schema.fields)):
                        field = schema.fields[k]
                        if field == schema.default_field:
                            channel_name = tag_value
                        else:
                            channel_name = '%s%s%s' % (tag_value, Schema.tag_field_separator, field)
                        channel_name_str = str(channel_name)
                        schema.add_channel(channel_name_str)
                        field_type = schema.channel_table[channel_name_str].get('type', None)
                        if (not schema.is_for_ts) and (field_type is None):
                            value = await self._get_first_data_value(schema.table, schema.tag, tag_value, field)
                            if value is not None:
                                schema.add_channel(channel_name_str, Schema.identify_datatype(value))


    async def _get_query_result(self, schema, channels, length, to, resampling=None, reducer=None, lastonly=False):
        result = {}
        stop = int(to)
        start = int(stop - float(length))
        
        if schema.time is None and not schema.is_for_obj:
            return result
            
        target_channels = []
        for name in channels:
            if not name.replace('.', '').replace('_', '').replace('-', '').replace(':', '').isalnum():
                logging.error('bad channel name: %s' % name)
            else:
                key = str(name[0:len(name)-len(schema.suffix)])
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

        query_result_columns, query_result_table = await self._execute_query(
            schema.table, 
            time_col, schema.time_type, time_from, time_to, 
            schema.tag, tag_values, fields,
            resampling=resampling, reducer=reducer, stop=stop,
            lastonly=lastonly
        )

        def add_result(channel, timestamp, value):
            if channel not in result:
                result[channel] = {
                    'start': start, 'length': int(length), 't': [], 'x': []
                }
            result[channel]['t'].append(int(1000*(timestamp-start))/1000.0)
            result[channel]['x'].append(DataSource.decode_if_json(value))
            
        remaining_channels = set(target_channels)
        for row in query_result_table:
            if len(remaining_channels) <= 0:
                break
            
            timestamp = row[0]
            if type(timestamp) == str:
                if timestamp.isdigit():
                    timestamp = float(timestamp)
                else:
                    timestamp = datetime.datetime.fromisoformat(timestamp)
            elif type(timestamp).__name__ == 'datetime':
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
