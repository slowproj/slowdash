# Created by Sanshiro Enomoto on 4 June 2022 #


import sys, os, time, logging, traceback
from sd_dataschema import Schema
from sd_datasource import DataSource

import couchdb


class DataSource_CouchDB(DataSource):
    def __init__(self, app, project, params):
        super().__init__(app, project, params)
        
        self.couch = None
        self.db = None
                
        dburl = Schema.parse_dburl(params.get('url', ''))
        self.server_url = 'http://{user}:{password}@{host}:{port}'.format(**dburl)
        self.db_name = dburl.get('db', None)
        if self.db_name is None:
            logging.error('CouchDB: No database entry found')

        def load_schema(params, entrytype):
            schema_list = []
            entry_list = params.get(entrytype, [])
            for entry in entry_list if type(entry_list) is list else [ entry_list ]:
                schema_conf = entry.get('schema', None)
                tag_values = entry.get('tags', {}).get('list', [])
                schema = Schema(schema_conf, tag_values)
                schema.name = entry.get('name', None)
                schema.suffix = entry.get('suffix', '')
                schema_list.append(schema)
            return schema_list

        self.ts_schemata = load_schema(params, 'time_series')
        self.objts_schemata = load_schema(params, 'object_time_series')
        self.viewtable_schemata = load_schema(params, 'view_table')
        self.viewtree_schemata = load_schema(params, 'view_tree')
        self.dbinfo_schemata = load_schema(params, 'database_info')

        self.channels_scaned = False
        self.server_connected = False
        

    def connect(self):
        if self.server_connected:
            return
        self.server_connected = True

        if self.server_url is None or self.db_name is None:
            return

        self.couch = couchdb.Server(self.server_url)
        for i in range(12):
            try:
                self.db = self.couch[self.db_name]
                break
            except Exception as e:
                logging.info(f'Unable to connect to CouchDB: {e}')
                logging.info(f'retrying in 5 sec... ({i+1}/12)')
                time.sleep(5)
        else:
            logging.error('Unable to connect to CouchDB "%s"' % self.db_name)
            logging.error(traceback.format_exc())
            self.db = None
                
        if self.db is not  None:
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
                    schema.add_channel(field, channel.get('type', None))

                    
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
                    channel_list[channel] = {'name': channel, 'type': Schema.identify_datatype(record[field]) }

            for field, channel in channel_list.items():
                schema.add_channel(field, channel.get('type', None))

        for schemata in [ self.ts_schemata, self.objts_schemata ]:
            for schema in schemata:
                schema.channel_table = {}
                if schema.table is None:
                    continue
                try:
                    view = self.db.view(schema.table)
                    if view.total_rows == 0:
                        continue
                except Exception as e:
                    logging.error('CouchDB: Unable to get view: "%s"' % schema.table)
                    continue
                scan_fields(schema, view)
                if schema.tag is not None:
                    if len(schema.tag_values) > 0:
                        for ch in schema.tag_values:
                            schema.add_channel(ch)
                    scan_tags(schema, view)

        couchdb_extra_entries = {
            'table': self.viewtable_schemata,
            'tree': self.viewtree_schemata,
            'tree': self.dbinfo_schemata
        }
        for datatype, schemata in couchdb_extra_entries.items():
            for schema in schemata:
                if schema.name is None:
                    schema.name = '%s_%s' % (datatype, schema.table.split('/')[-1])
                schema.add_channel(schema.name, datatype)

        self.channels_scaned = True

                    
    def get_channels(self):
        self.scan_channels()
            
        channels = []
        for schemata in [
                self.ts_schemata, self.objts_schemata,
                self.viewtable_schemata, self.viewtree_schemata,
                self.dbinfo_schemata
        ]:
            for schema in schemata:
                for ch in schema.channel_table.values():
                    ch['name'] = ch['name'] + schema.suffix
                    channels.append(ch)

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
            
        # DB info as a tree (CURRENT data, valid only for "now")
        now = time.time()
        for schema in self.dbinfo_schemata:
            name = schema.name
            if name not in channels:
                continue
            if self.db is None:
                continue

            tree = {}
            if now >= start and now < to + 5:
                try:
                    info = self.db.info()
                    tree['Name'] = info.get('db_name', '')
                    tree['DocumentCount'] = info.get('doc_count', -1)
                    tree['FileSize_GB'] = '%.3f' % (float(info.get('sizes', {}).get('file', -1))/1e9)
                    tree['ExternalSize_GB'] = '%.3f' % (float(info.get('sizes', {}).get('external', -1))/1e9)
                except:
                    pass
            
            result[name] = {
                'start': start, 'length': int(length), 't': now - start, 'x': { 'tree': tree }
            }
            
        return result


    def execute_timeseries_query(self, schema, channels, length, to, lastonly):
        if not self.channels_scaned:
            self.scan_channels()

        result = {}
        def load_data(timestamp, channel, value):
            channel_name = channel + schema.suffix
            if channel_name not in result:
                result[channel_name] = {
                    'start': start, 'length': int(length), 't': [], 'x': []
                }
            result[channel_name]['t'].append(int(10*(timestamp-start))/10)
            result[channel_name]['x'].append(DataSource.decode_if_json(value))
        
        start = to - length
        view_name = schema.table

        target_channels = []
        for name in channels:
            if not name.replace('.', '').replace('_', '').replace('-', '').replace(':', '').isalnum():
                logging.error('bad channel name: %s' % name)
            else:
                key = name[0:len(name)-len(schema.suffix)]
                if key in schema.channel_table:
                    target_channels.append(key)
        
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

    
    def get_blob(self, channel, blob_id):
        if not self.server_connected:
            self.connect()
        if self.db is None:
            return (None, None)
        
        if channel not in [ch.get('name', ' ') for ch in self.get_channels()]:
            return (None, None)
        
        path = blob_id.split('/')
        if len(path) < 2:
            return (None, None)
        doc_id, att_name = path[0], path[1]
        
        doc = self.db.get(doc_id)
        if doc is None:
            return (None, None)
        content_type = doc.get('_attachments', {}).get(att_name, {}).get('content_type', None)
        if content_type is None:
            return (None, None)
        att = self.db.get_attachment(doc, att_name, default=None)
        if att is None:
            return (None, None)

        content = att.read()
        att.close()
        
        return (content_type, content)
