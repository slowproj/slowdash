# Created by Sanshiro Enomoto on 16 May 2024 #


import os, sys, time, logging
from .base import DataStore



    
class DataStore_CSV(DataStore):
    def __init__(self, db_url='csv:///SlowStore.d', ts_table_name=None, obj_table_name=None, objts_table_name=None, recreate=False):
        self.db_url = db_url
        self.ts_table_name = ts_table_name
        self.obj_table_name = obj_table_name
        self.objts_table_name = objts_table_name
        self.flag = "w" if recreate else "a"

        dirname = self.db_url[7:] if self.db_url.startswith('csv:///') else self.db_url
        while len(dirname) > 0 and dirname[0] == '/':
            dirname = dirname[1:]
        dirname = os.path.abspath(dirname)
        if not os.path.isdir(dirname):
            try:
                os.makedirs(dirname)
            except:
                logging.error('unable to create directory: ' + dirname)

        self.ts_file = None
        if self.ts_table_name is not None:
            filename = os.path.join(dirname, ts_table_name+".csv")
            is_new = recreate or not os.path.isfile(filename)
            try:
                self.ts_file = open(filename, self.flag)
                if is_new:
                    self.ts_file.write('timestamp,channel,value\n')
            except Exception as e:
                logging.error('unable to create a CSV file: %s: %s' % (filename, str(e)))
                self.ts_file = None

        self.obj_file = None
        self.obj_list = {}
        if self.obj_table_name is not None:
            filename = os.path.join(dirname, obj_table_name+".csv")
            is_new = recreate or not os.path.isfile(filename)
            if not is_new:
                try:
                    obj_file = open(filename, "r")
                    headder = obj_file.readline()
                    for line in obj_file:
                        channel, value = line.rstrip('\n').split(',', 1)
                        self.obj_list[channel] = value
                except Exception as e:
                    pass
            try:
                self.obj_file = open(filename, "w")
            except Exception as e:
                logging.error('unable to create a CSV file: %s: %s' % (filename, str(e)))
                self.obj_file = None
            self.obj_file.truncate()
                
        self.objts_file = None
        if self.objts_table_name is not None:
            filename = os.path.join(dirname, objts_table_name+".csv")
            is_new = recreate or not os.path.isfile(filename)
            try:
                self.objts_file = open(filename, self.flag)
                if is_new:
                    self.objts_file.write('timestamp,channel,value\n')
            except Exception as e:
                logging.error('unable to create a CSV file: %s: %s' % (filename, str(e)))
                self.objts_file = None

            
    def __del__(self):
        if self.ts_file is not None:
            self.ts_file.close()
        if self.obj_file is not None:
            self.obj_file.close()
        if self.objts_file is not None:
            self.objts_file.close()


    def write_timeseries(self, fields, tag=None, timestamp=None):
        if self.ts_file is None:
            return
        
        if timestamp is None:
            timestamp = time.time()

        if not isinstance(fields, dict):
            if tag is None:
                return
            self.ts_file.write("%d,%s,%f\n" % (timestamp, self._escape(tag), fields))
        else:
            for k, v in fields.items():
                ch = k if tag is None else "%s:%s" % (tag, k)
                self.ts_file.write("%d,%s,%f\n" % (timestamp, self._escape(ch), v))
        self.ts_file.flush()
                    
    
    def write_object(self, obj, name=None):
        if self.obj_file is None:
            return

        if name is None:
            name = obj.name
        self.obj_list[self._escape(name)] = self._escape(str(obj))

        self.obj_file.truncate(0)
        self.obj_file.seek(0)
        self.obj_file.write('channel,value\n')
        for channel,value in self.obj_list.items():
            self.obj_file.write("%s,%s\n" % (channel, value))
        self.obj_file.flush()

        
    def write_object_timeseries(self, obj, timestamp=None, name=None):
        if self.objts_file is None:
            return
        
        if timestamp is None:
            timestamp = time.time()
        if name is None:
            name = obj.name
            
        self.objts_file.write("%d,%s,%s\n" % (timestamp, self._escape(name), self._escape(str(obj))))
        self.objts_file.flush()


    def _escape(self, text):
        # TODO: do not replace "\," with "\\,"
        return text.replace(',', '\\,')



class DataStore_TextDump(DataStore_CSV):
    def __init__(self, output=sys.stdout):
        self.ts_file = output
        self.obj_file = output
        self.objts_file = output

        
    def write_object(self, obj, name=None):
        if name is None:
            name = obj.name
        self.objts_file.write("%s,%s\n" % (self._escape(name), self._escape(str(obj))))

    def _escape(self, text):
        return text
        
