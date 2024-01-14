# Created by Sanshiro Enomoto on 4 June 2022 #


import sys, os, time, logging, traceback
from datasource import DataSource, Schema

import couchdb



class DataSource_CouchDB(DataSource):
    def __init__(self, project_config, config):
        super().__init__(project_config, config)
        
        self.couch = None
        self.db = None
                
        dburl = Schema.parse_dburl(self.config.get('url', ''))
        self.server_url = 'http://{user}:{password}@{host}:{port}'.format(**dburl)
        self.db_name = dburl.get('db', None)
        if self.db_name is None:
            logging.error('CouchDB: No database entry found')

        def load_schema(config, entrytype):
            schema_list = []
            entry_list = config.get(entrytype, [])
            for entry in entry_list if type(entry_list) is list else [ entry_list ]:
                schema_conf = entry.get('schema', None)
                tag_values = entry.get('tags', {}).get('list', [])
                schema = Schema(schema_conf, tag_values)
                schema.name = entry.get('name', None)
                schema_list.append(schema)
            return schema_list

        self.ts_schemata = load_schema(config, 'time_series')
        self.objts_schemata = load_schema(config, 'object_time_series')
        self.viewtable_schemata = load_schema(config, 'view_table')
        self.viewtree_schemata = load_schema(config, 'view_tree')

        self.channels_scaned = False
        self.server_connected = False
        

    def connect(self):
        if self.server_connected:
            return
        self.server_connected = True

        if self.server_url is None or self.db_name is None:
            return
            
        try:
            self.couch = couchdb.Server(self.server_url)
            self.db = self.couch[self.db_name]
        except Exception as e:
            logging.error('Unable to connect to CouchDB: %s' % str(e))
            logging.error(traceback.format_exc())
            self.db = None
                
        logging.info('connected to CoudhDB, server: %s, db: %s' % (self.server_url, self.db_name))
            
        
    def scan_channels(self):
        if not self.server_connected:
            self.connect()
        if self.db is None:
            return

        def scan_fields(schema, view):
            channel_list = {}
            
            # read field definitions in the schema first
            all_fields_have_types = True
            for k in range(len(schema.fields)):
                field = schema.fields[k]
                channel_list[field] = { 'name': field }
                if schema.field_types[k] is not None:
                    channel_list[field]['type'] = schema.field_types[k]
                else:
                    all_fields_have_types = False

            # scan one data record
            if len(channel_list) == 0 or not all_fields_have_types:
                record = view.rows[-1].value
                for field in record:
                    if len(schema.fields) > 0 and field not in schema.fields:
                        continue
                    if field in [ schema.tag ] + schema.flags:
                        continue
                    if field not in channel_list:
                        channel_list[field] = { 'name': field }
                    if 'type' not in channel_list[field]:
                        channel_list[field]['type'] = Schema.identify_datatype(record[field])
                        
            # update schema
            if len(schema.fields) == 0:
                schema.fields += channel_list.keys()
                schema.field_types += [ None for k in range(len(schema.fields)) ]
                if len(schema.fields) == 1:
                    schema.default_field = schema.fields[0]
            for k in range(len(schema.fields)):
                if schema.field_types[k] is None:
                    schema.field_types[k] = channel_list[schema.fields[k]]['type']

            if schema.tag is None:
                for field, channel in channel_list.items():
                    if field not in schema.channel_table:
                        schema.channel_table[field] = channel
                    elif 'type' not in schema.channel_table[field]:
                        schema.channel_table[field]['type'] = channel['type']

                    
        def scan_tags(schema, view):
            if schema.tag is None:
                return
            
            channel_list = {}
            tag_value_set = set()
            
            last_timestamp = view.rows[-1].key
            scan_from = last_timestamp - 3660
            for row in reversed(view[scan_from:last_timestamp+1].rows):
                record = row.value
                tag_value = record.get(schema.tag, None)
                if tag_value is None or tag_value in tag_value_set:
                    continue
                tag_value_set.add(tag_value)
                for field in record:
                    if field == schema.tag:
                        continue
                    if field == schema.default_field:
                        channel = tag_value
                    else:
                        channel = '%s%s%s' % (tag_value, Schema.tag_field_separator, field)
                    if channel in channel_list:
                        continue
                    value = record.get(field, None)
                    if value is None:
                        continue
                    datatype = Schema.identify_datatype(record[field])
                    channel_list[channel] = {'name': channel, 'type': datatype}

            for field, channel in channel_list.items():
                if field not in schema.channel_table:
                    schema.channel_table[field] = channel
                elif 'type' not in schema.channel_table[field]:
                    schema.channel_table[field]['type'] = channel['type']
                    
        for schemata in [ self.ts_schemata, self.objts_schemata ]:
            for schema in schemata:
                schema.channel_table = {}
                if schema.table is None:
                    continue
                try:
                    view = self.db.view(schema.table)
                except Exception as e:
                    logging.error('CouchDB: Unable to get view: "%s"' % schema.table)
                    continue
                if view.total_rows == 0:
                    continue
                scan_fields(schema, view)
                if schema.tag is not None:
                    if len(schema.tag_values) > 0:
                        for ch in schema.tag_values:
                            schema.channel_table[ch] = { "name": ch }
                    scan_tags(schema, view)

        for datatype, schemata in { 'table': self.viewtable_schemata, 'tree': self.viewtree_schemata }.items():
            for schema in schemata:
                if schema.name is None:
                    schema.name = '%s_%s' % (datatype, schema.table.split('/')[-1])
                schema.channel_table = {schema.name: { "name": schema.name, 'type': datatype }}

        self.channels_scaned = True

                    
    def get_channels(self):
        self.scan_channels()
            
        channels = []
        for schemata in [ self.ts_schemata, self.objts_schemata, self.viewtable_schemata, self.viewtree_schemata ]:
            for schema in schemata:
                channels += schema.channel_table.values()

        return channels
            
    
    def get_timeseries(self, channels, length, to, resampling=None, reducer='last'):
        if not self.server_connected:
            self.connect()
        if self.db is None:
            return None
            
        result = {}
        for schema in self.ts_schemata:
            result.update(self.execute_timeseries_query(schema, channels, length, to, lastonly=False))
        
        if resampling is not None and resampling <= 0:
            return self.resample(result, length, to, resampling, reducer)
        else:
            return result

    
    def get_object(self, channels, length, to):
        if not self.server_connected:
            self.connect()
        if self.db is None:
            return None
            
        result = {}
        for schema in self.objts_schemata:
            result.update(self.execute_timeseries_query(schema, channels, length, to, lastonly=True))
        
        start = to - length
        
        # view rows as a table
        max_number_of_rows = 1024
        for schema in self.viewtable_schemata:
            view_name = schema.table
            name = schema.name
            if name not in channels:
                continue
            rows = self.db.view(view_name)[start:to].rows

            columns = schema.fields
            if len(columns) == 0 and len(rows) > 0:
                columns = [ c for c in rows[-1].value.keys() ]
            
            table = []
            n = len(rows)
            offset = max(0, n - max_number_of_rows)
            for k in range(offset, n):
                row = rows[k]
                timestamp, record = row.key, row.value
                table.append([timestamp] + [ record.get(key, None) for key in columns ])
            result[name] = {
                'start': start, 'length': int(length), 't': to, 'x': {
                    'columns': ['_key'] + columns,
                    'table': table
                }
            }
            
        # view row as a tree
        for schema in self.viewtree_schemata:
            view_name = schema.table
            name = schema.name
            if name not in channels:
                continue

            rows = self.db.view(view_name)[start:to].rows
            if len(rows) == 0:
                continue
            row = rows[-1]
            timestamp, record = row.key, row.value
            
            columns = schema.fields
            if len(columns) == 0:
                columns = [ c for c in record.keys() ]
            
            tree = {
                '_key': timestamp
            }
            for key in columns:
                tree[key] = record.get(key, None)
            
            result[name] = {
                'start': start, 'length': int(length), 't': timestamp, 'x': { 'tree': tree }
            }
            
        return result


    def execute_timeseries_query(self, schema, channels, length, to, lastonly):
        if not self.channels_scaned:
            self.scan_channels()

        result = {}
        def load_data(timestamp, channel, value):
            if channel not in result:
                result[channel] = {
                    'start': start, 'length': int(length), 't': [], 'x': []
                }
            result[channel]['t'].append(int(10*(timestamp-start))/10)
            result[channel]['x'].append(value)
        
        start = to - length
        view_name = schema.table
        target_channels = set(schema.channel_table.keys()) & set(channels)
        
        rows = self.db.view(view_name)[start:to].rows
        if lastonly:
            # TOOD: make this more efficient, not to load the entire rows
            rows = reversed(rows)

        for row in rows:
            if len(target_channels) <= 0:
                break
            timestamp, record = row.key, row.value
            for field in record:
                if schema.tag is None:
                    if field not in target_channels:
                        continue
                    value = row.value.get(field, None)
                    if value is None:
                        continue
                    load_data(timestamp, field, value)
                    if lastonly:
                        target_channels.remove(field)
                else:
                    tag_value = record.get(schema.tag, None)
                    channel_names = [ '%s%s%s' % (tag_value, Schema.tag_field_separator, field) ]
                    if field == schema.default_field:
                        channel_names.append(tag_value)
                    for channel in channel_names:
                        if channel not in target_channels:
                            continue
                        value = record.get(field, None)
                        if value is None:
                            continue
                        load_data(timestamp, channel, value)
                        if lastonly:
                            target_channels.remove(channel)

        return result

    
    def get_blob(self, channel, params, output):
        if not self.server_connected:
            self.connect()
        if self.db is None:
            return None

        if len(params) < 2:
            return None
        doc_id, att_name = params[0], params[1]
        
        doc = self.db.get(doc_id)
        if doc is None:
            return None
        content_type = doc.get('_attachments', {}).get(att_name, {}).get('content_type', None)
        if content_type is None:
            return None
        att = self.db.get_attachment(doc, att_name, default=None)
        if att is None:
            return None

        output.write(att.read())
        att.close()
        
        return content_type
    
