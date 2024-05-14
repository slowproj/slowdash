# Created by Sanshiro Enomoto on 10 April 2023 #


import sys, os, logging
from datasource import DataSource, Schema


class DataSource_TableStore(DataSource):
    def __init__(self, project_config, config):
        super().__init__(project_config, config)
        self.timeseries_table = None
        
        self._configure(project_config, config)        
        self.channels_scanned = False

        
    # override this
    def _get_tag_values_from_data(self, schema):
        return None

    
    # override this
    def _get_first_data_row(self, schema):
        columns, record = None, []
        return columns, record

    
    # override this
    def _get_first_data_value(self, table, tag_name, tag_value, field):
        return None

        
    # override this
    def _execute_query(self, schema, channels, length, to, resampling=None, reducer=None, lastonly=False):
        return {}

    
    def get_channels(self):
        self._scan_channels()
            
        channels = []
        for schema in self.ts_schemata + self.obj_schemata + self.objts_schemata:
            for ch in schema.channel_table.values():
                if 'type' in ch:
                    channels.append({ 'name': ch['name'] + schema.suffix, 'type': ch['type'] })
                else:
                    channels.append({ 'name': ch['name'] + schema.suffix })
                
        return channels
        
    
    def get_timeseries(self, channels, length, to, resampling=None, reducer='last'):
        if not self.channels_scanned:
            self._scan_channels()
        
        result = {}
        for schema in self.ts_schemata:
            result.update(self._execute_query(
                schema, channels, length, to, resampling=resampling, reducer=reducer, lastonly=False
            ))
            
        if resampling is None:
            return result
            
        return self.resample(result, length, to, resampling, reducer)

    
    def get_object(self, channels, length, to):
        result = {}
        for schema in self.obj_schemata + self.objts_schemata:
            if schema.tag is None:
                result.update(self._execute_query(
                    schema, channels, length, to, resampling=None, reducer=None, lastonly=True
                ))
            else:
                # to make use of "limit 1"
                for ch in channels:  
                    result.update(self._execute_query(
                        schema, [ch], length, to, resampling=None, reducer=None, lastonly=True
                    ))
            # retry if the value is null?
            
        return result

    
    def _configure(self, project_config, config):
        def load_schema(config, entrytype):
            schema_list = []
            entry_list = config.get(entrytype, [])
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

        self.ts_schemata = load_schema(config, 'time_series')
        self.obj_schemata = load_schema(config, 'object')
        self.objts_schemata = load_schema(config, 'object_time_series')

        
    def _scan_channels(self):
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
                logging.warn('schema: time type not specified: "with timezone" is assumed')
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
                tag_values = self._get_tag_values_from_data(schema)
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
                columns, record = self._get_first_data_row(schema.table)
                if columns is None:
                    self.channels_scanned = False  # maybe the table is not created yet. Try again later
                    continue
                    
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
                        schema.add_channel(channel_name)
                        field_type = schema.channel_table[channel_name].get('type', None)
                        if (not schema.is_for_ts) and (field_type is None):
                            value = self.get_first_data_value(schema.table, schema.tag, tag_value, field)
                            if value is not None:
                                schema.add_channel(channel_name, Schema.identify_datatype(value))
