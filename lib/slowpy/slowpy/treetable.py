# Created by Sanshiro Enomoto on 17 July 2024 #


import datetime
from .basetypes import DataElement


class Tree(DataElement):
    def __init__(self, path_delimiter='/'):
        super().__init__()
        self.path_delimiter = path_delimiter
        self.tree = {}

        
    def clear(self):
        super().clear()
        self.tree = {}

        
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
                
        add(self.tree, key.split(self.path_delimiter), value)

        
    def to_json(self):
        return { **super().to_json(),  **{
            'tree': self.tree
        }}

    
    @staticmethod
    def from_json(obj):
        return None


    
class Table(DataElement):
    def __init__(self, columns):
        super().__init__()
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
    def from_json(obj):
        return None
