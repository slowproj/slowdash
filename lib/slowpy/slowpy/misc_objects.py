# Created by Sanshiro Enomoto on 17 July 2024 #


import datetime
from .basetypes import DataElement


class Table(DataElement):
    def __init__(self, name, columns):
        super().__init__()
        self.name = name
        self.columns = columns
        self.tabular = []

        
    def clear(self):
        super().clear()
        self.tabular = []

        
    def add_row(self, array_of_values):
        self.tabular.append(array_of_values)

        
    def to_json(self):
        return { **super().to_json(),  **{
            'columns': self.columns,
            'table': self.tabular
        }}

    
    @staticmethod
    def from_json(name, obj):
        return None

    
    
class Log(Table):
    def __init__(self, name="Log", dateformat='%a, %b %d %Y, %H:%M:%S'):
        super().__init__(name, columns=['Level', 'Time', 'Message'])
        self.dateformat = dateformat

        
    def write(self, level, message):
        self.tabular.append([ level, datetime.datetime.now().strftime(self.dateformat), message ])

        
    def debug(self, message):
        self.write('Debug', message)

        
    def info(self, message):
        self.write('Info', message)

        
    def warn(self, message):
        self.write('Warn', message)

        
    def error(self, message):
        self.write('Error', message)


    
class Record(DataElement):
    def __init__(self, name, path_delimiter='/'):
        super().__init__()
        self.name = name
        self.path_delimiter = path_delimiter
        self.record = {}

        
    def clear(self):
        super().clear()
        self.record = {}

        
    def set(self, key, value):
        def add(node, path, value):
            if len(path) < 1:
                pass
            if len(path) == 1:
                node[path[0]] = value
            elif len(path) > 1:
                if path[0] not in node:
                    node[path[0]] = {}
                add(node[path[0]], path[1:], value)
        add(self.record, key.split(self.path_delimiter), value)

        
    def to_json(self):
        return { **super().to_json(),  **{
            'tree': self.record
        }}

    
    @staticmethod
    def from_json(name, obj):
        return None

    
