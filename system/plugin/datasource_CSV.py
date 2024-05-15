# Created by Sanshiro Enomoto on 13 May 2024 #


import sys, os, time, glob, logging
from datasource import DataSource, Schema
from datasource_TableStore import DataSource_TableStore

    
class DataSource_CSV(DataSource_TableStore):
    def __init__(self, project_config, config):
        self.directory = None
        self.time_sep = 'T'
        
        dburl = Schema.parse_dburl(config.get('url', ''))
        directory = config.get('directory', dburl.get('db', None))
        if directory is None:
            directory = '.'
        
        if os.path.isdir(directory) and os.access(directory, os.R_OK):
            self.directory = directory
        else:
            logging.error('invalid CSV directory: %s' % directory)
            return

        super().__init__(project_config, config)

        
    def _configure(self, project_config, config):
        if self.directory is None:
            return

        super()._configure(project_config, config)




        ### TABLES ###
        self.tables = {}
        tables = config.get('table', [])
        if type(tables) is not list:
            tables = [tables]
        if len(tables) < 1:
            for filepath in sorted(glob.glob(os.path.join(self.directory, "*.csv"))):
                if os.path.isfile(filepath) and os.access(filepath, os.R_OK):
                    name = os.path.basename(filepath)
                    tables.append({'name': name, 'file': filepath})                

        for table in tables:
            if not (('name' in table) and ('file' in table)):
                logging.error('table needs "name" and "file" fields: "%s"' % table)
                continue
            self.tables[table['name']] = {
                'file': table['file'],
                'head': table.get('head', 128),
                'tail': table.get('tail', None)
            }


    def _get_tag_values_from_data(self, schema):
        if self.directory is None:
            return None
        
        columns, tag_value_set = None, set()
        tag_column = None
        filepath = os.path.join(self.directory, schema.table + '.csv')
        try:
            with open(filepath) as f:
                for line in f:
                    if columns is None:
                        columns = self._split(line)
                        for k in range(len(columns)):
                            if columns[k] == schema.tag:
                                tag_column = k
                                break
                        else:
                            logging.error('unable to find tag column: %s: %s' % (schema.tag, filepath))
                            return None
                    else:
                         tag_value_set.add(self._split(line)[tag_column])
        except Exception as e:
            logging.error('unable to read CSV file: %s: %s', (filepath, str(e)))
            return None
        
        return sorted([ tag for tag in tag_value_set ])

    
    def _get_first_data_row(self, schema):
        if self.directory is None:
            return None, []
        
        columns, record = None, []
        filepath = os.path.join(self.directory, schema.table + '.csv')
        try:
            with open(filepath) as f:
                for line in f:
                    if columns is None:
                        columns = self._split(line)
                    else:
                        record = self._split(line)
                        break
        except Exception as e:
            logging.error('unable to read CSV file: %s: %s', (filepath, str(e)))
            return None, []
        
        return columns, record

    
    def _get_first_data_value(self, table, tag_name, tag_value, field):
        if self.directory is None:
            return None

        value = None
        columns, tag_column, value_column = None, None, None
        filepath = os.path.join(self.directory, table + '.csv')
        try:
            with open(filepath) as f:
                for line in f:
                    if columns is None:
                        columns = self._split(line)
                        for k in range(len(columns)):
                            if columns[k] == tag_name:
                                tag_column = k
                            elif columns[k] == field:
                                field_column = k
                        if tag_column is None:
                            logging.error('unable to find tag column: %s: %s' % (tag_name, filepath))
                            return None
                        if field_column is None:
                            logging.error('unable to find field column: %s: %s' % (field, filepath))
                            return None
                    else:
                        record = self._split(line)
                        if record[tag_column] == tag_value:
                            value = record[field_column]
                            break
                            
        except Exception as e:
            logging.error('unable to read CSV file: %s: %s', (filepath, str(e)))
            return None
        
        return value

        
    def _execute_query(self, table_name, time_col, time_from, time_to, tag_col, tag_values, fields, resampling=None, reducer=None, stop=None, lastonly=False):
        columns, table = None, []

        time_from, time_to = int(time_from), int(time_to)
        time_column, tag_column, field_columns = None, None, []
        filepath = os.path.join(self.directory, table_name + '.csv')
        try:
            with open(filepath) as f:
                for line in f:
                    if columns is None:
                        columns = self._split(line)
                        for k in range(len(columns)):
                            if time_col is not None and (columns[k] == time_col):
                                time_column = k
                            elif tag_col is not None and (columns[k] == tag_col):
                                tag_column = k
                            elif columns[k] in fields:
                                field_columns.append(k)
                    else:
                        record = self._split(line)                        
                        time_val = int(record[time_column]) if time_column is not None else int(time.time())
                        if time_column is not None and (time_val < time_from or time_val >= time_to):
                            continue
                        row = [ time_val ]
                        if tag_column is not None:
                            if record[tag_column] not in tag_values:
                                continue
                            else:
                                row.append(record[tag_column])
                        row += [ record[k] for k in field_columns ]
                        if lastonly and len(table) > 0:
                            table[0] = record
                        else:
                            table.append(row)
        except Exception as e:
            logging.error('unable to read CSV file: %s: %s', (filepath, str(e)))
            return [], []
        
        return columns, table

    
    def get_channels(self):
        channels = super().get_channels()
        channels += [ {'name': name, 'type': 'table'} for name in self.tables ]

        return channels
        
    
    def get_object(self, channels, length, to):
        result = super().get_object(channels, length, to)

        ### TABLES ###
        for ch in channels:
            if ch not in self.tables:
                continue
            entry = self.tables[ch]
            filepath = entry['file']
            head = entry.get('head', None)
            tail = entry.get('tail', None)
            try:
                columns, table = None, []
                with open(filepath) as f:
                    for line in f:
                        if columns is None:
                            columns = self._split(line)
                        else:
                            table.append(self._split(line))
                        if head is not None and len(table) >= head:
                            break
                        # TODO: tail
                result[ch] = { 
                    'start': to-length, 'length': length,
                    't': to,
                    'x': { 'columns': columns, 'table': table }
                }
            except Exception as e:
                logging.error('unable to read CSV file: %s: %s', (filepath, str(e)))
                pass
            
        return result


    def _split(self, line):
        result = []
        token = ''
        is_escaped = False
        for ch in line:
            if is_escaped:
                token += ch
                is_escaped = False
            elif ch == '\\':
                is_escaped = True
            elif ch == ',':
                result.append(token)
                token = ''
            else:
                if ch != '\n':
                    token += ch
        result.append(token)
        
        return result
