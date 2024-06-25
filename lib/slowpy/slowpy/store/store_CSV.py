# Created by Sanshiro Enomoto on 16 May 2024 #


import os, sys, time, logging
from .base import DataStore


class DataStore_CSV(DataStore):
    def __init__(self, db_url, table, recreate=False):
        '''
        - db_url: directory for the CSV files. Example: 'csv:///SlowStore.d' for dir name SlowStore.d
        - table: file root name of the CSV file. Example: 'test' for file name 'test.csv'
        '''
        self.db_url = db_url
        self.table = table
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

        self.csv_file = None
        if self.table is not None:
            filename = os.path.join(dirname, table+".csv")
            is_new = recreate or not os.path.isfile(filename)
            try:
                self.csv_file = open(filename, self.flag)
                if is_new:
                    self.csv_file.write('timestamp,channel,value\n')
            except Exception as e:
                logging.error('unable to create a CSV file: %s: %s' % (filename, str(e)))
                self.csv_file = None

        self.update_error_shown = False

            
    def __del__(self):
        if self.csv_file is not None:
            self.csv_file.close()


    def another(self, table, recreate=None):
        if recreate is None:
            recreate = (self.flag == "w")

        return DataStore_CSV(self.db_url, table, recreate)

        
    def _open_transaction(self):
        return self.csv_file

    
    def _close_transaction(self, redis):
        pass

    
    def _write_one(self, csv_file, timestamp, tag, fields, values, update):
        if update is True and self.update_error_shown is False:
            logging.error('CSV: "update()" is not available for CSV: switched to append()')
            self.update_error_shown = True
                
        channels = self._channels(tag, fields)
        for i in range(min(len(channels), len(values))):
            ch = self._escape(channels[i])
            value = self._escape(str(values[i]))
            self.csv_file.write("%d,%s,%s\n" % (int(timestamp), ch, value))
        self.csv_file.flush()

        
    def _escape(self, text):
        # TODO: do not replace "\," with "\\,"
        return text.replace(',', '\\,')



class DataStore_TextDump(DataStore_CSV):
    def __init__(self, output=sys.stdout):
        self.csv_file = output

        
    def _escape(self, text):
        return text
        
