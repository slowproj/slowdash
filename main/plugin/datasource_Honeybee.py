# Created by Sanshiro Enomoto on 20 March 2022 #


import sys, os, json, logging, subprocess
from datasource import DataSource
    
    
class DataSource_Honeybee(DataSource):
    def __init__(self, project_config, config):
        super().__init__(project_config, config)
        self.bin_dir = self.config.get('bin_dir', None)
        self.config_file = self.config.get('config', None)
        self.dripline_db = self.config.get('dripline_db', None)
        if self.bin_dir is not None:
            self.bin_dir = os.path.join(project_config.project_dir, self.bin_dir)
        if self.config_file is not None:
            self.config_file = os.path.join(project_config.project_dir, self.config_file)

            
    def get_channels(self):
        cmd = [ os.path.join(self.bin_dir, 'hb-list-sensors') ]
        cmd.append('--config=' + self.config_file)
        if self.dripline_db is not None:
            cmd.append('--dripline-db=' + self.dripline_db)
        cmd.append('--fields=name')
        try:
            return json.loads(self.execute(cmd))
        except Exception as e:
            logging.error('error on parsing JSON: %s' % str(e))
            return []

    
    def get_timeseries(self, channels, length, to, resampling=None, reducer='last'):
        cmd = [ os.path.join(self.bin_dir, 'hb-get-data') ]
        cmd.extend(channels)
        cmd.append('--series')
        cmd.append('--length=%f' % length)
        if to is not None:
            cmd.append('--to-ts=%f' % to)
        if resampling is not None:
            cmd.append('--resample=%s,%s' % (resampling, reducer))
        cmd.append('--config=' + self.config_file)
        if self.dripline_db is not None:
            cmd.append('--dripline-db=' + self.dripline_db)
        try:
            output = self.execute(cmd)
        except Exception as e:
            logging.error('error on executing honeybee command: %s' % str(e))
            return None
        try:
            result = json.loads(output)
        except Exception as e:
            logging.error('error on parsing JSON: %s' % str(e))
            return None

        non_existent_channels = []
        for ch in result:
            x = result[ch].get('x', [])
            if type(x) is not list or len(x) < 1:
                non_existent_channels.append(ch)
        for ch in non_existent_channels:
            del result[ch]

        return result

                
    def execute(self, cmd):
        try:
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                check=True,
                encoding='utf-8'
            )
            result = process.stdout
        except Exception as e:
            logging.error(str(e))
            return None
        
        return result
