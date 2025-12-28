# Created by Sanshiro Enomoto on 20 March 2022 #


import sys, os, asyncio, json, logging
from sd_datasource import DataSource
    
    
class DataSource_Honeybee(DataSource):
    def __init__(self, app, project, params):
        super().__init__(app, project, params)
        self.bin_dir = params.get('bin_dir', None)
        self.config_file = params.get('config', None)
        self.dripline_db = params.get('dripline_db', None)
        if self.bin_dir is not None:
            self.bin_dir = os.path.join(project.project_dir, self.bin_dir)
        if self.config_file is not None:
            self.config_file = os.path.join(project.project_dir, self.config_file)

            
    async def aio_get_channels(self):
        cmd = [ os.path.join(self.bin_dir, 'hb-list-sensors') ]
        cmd.append('--config=' + self.config_file)
        if self.dripline_db is not None:
            cmd.append('--dripline-db=' + self.dripline_db)
        cmd.append('--fields=name')
        try:
            output = await self.execute(*cmd)
        except Exception as e:
            logging.error('error on executing honeybee command: %s' % str(e))
            return []
        try:
            if len(output) > 0:
                result = json.loads(output)
            else:
                result = []
        except Exception as e:
            logging.error('error on parsing JSON: %s' % str(e))
            return []

        return result

    
    async def aio_get_timeseries(self, channels, length, to, resampling=None, reducer='last', filler='fillna', envelope=0):
        if envelope > 0:
            db_resampling = None
        else:
            db_resampling = resampling
        
        cmd = [ os.path.join(self.bin_dir, 'hb-get-data') ]
        cmd.extend(channels)
        cmd.append('--series')
        cmd.append('--length=%f' % length)
        if to is not None:
            cmd.append('--to-ts=%f' % to)
        if db_resampling is not None:
            cmd.append('--resample=%s,%s' % (db_resampling, reducer))
        cmd.append('--config=' + self.config_file)
        if self.dripline_db is not None:
            cmd.append('--dripline-db=' + self.dripline_db)
        try:
            output = await self.execute(*cmd)
        except Exception as e:
            logging.error('error on executing honeybee command: %s' % str(e))
            return None
        try:
            if len(output) > 0:
                result = json.loads(output)
            else:
                result = {}
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

        if resampling is None:
            return result
        if db_resampling is not None and db_resampling > 0:
            # resampling applied in DB
            return result
        
        return self.resample(result, length, to, resampling, reducer, filler, envelope)

                
    async def execute(self, *cmd):
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                logging.error(f'Honeybee: {stderr.decode()}')
                return None
            return stdout.decode()
        except Exception as e:
            logging.error(str(e))
            return None
