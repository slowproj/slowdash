# Created by Sanshiro Enomoto on 3 June 2023 #


class DataStore:
    
    def write_timeseries(self, fields, tag=None, timestamp=None):
        pass
    
    def write_object(self, obj, name=None):
        pass

    def write_object_timeseries(self, obj, timestamp=None, name=None):
        pass


    
class DataStore_Null(DataStore):
    pass

