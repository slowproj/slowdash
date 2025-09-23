# Created by Sanshiro Enomoto on 19 September 2025 #


import sys, os, inspect, logging
import numpy as np
from .store import DataStore


class DataStore_HDF5(DataStore):
    """
    Writes time-series data to an HDF5 file in a wide, row-append format
    using a NumPy compound dtypes (timestamp + channels)
    
    Parameters
    ----------
      db_url : str
          path to the HDF5 file. Example: 'hdf5:///path/to/file.hdf5
      dataset : str
          HDF "dataset" name
      fields : Dict(str, default_value), Dict(str, type), or None
          Data fields, such as { 'ch00': np.int32(-1), 'ch01': np.int32(-1), ... }
          If None, inferred from the first data record.
      flush_every : str
          buffer rows before flushing to disk
      chunk_rows : int
          dataset chunk size in rows
      compression : str|None
          'lzf' (fast) or 'gzip'
    
    Notes
    -----
      - Field names and types are inferred from the first record appended
      - `another(dataset)` creates another dataset in the same HDF5 file
      - The HDF5 file are readable by multiple processes while writing (SWMR mode)
    """

    def __init__(self, db_url:str, dataset:str, fields=None, *, recreate=False, flush_every=128, chunk_rows=8192, compression='lzf'):
        super().__init__()
        
        self.filepath = db_url[8:] if db_url.startswith('hdf5://') else db_url
        self.dataname = str(dataset) or 'SlowData'
        self.flush_every = int(flush_every)
        self.chunk_rows = int(chunk_rows)
        self.compression = compression
        
        self.hdf5_file = None
        self.file_holder = self
        
        self.dataset = None
        self.fields = []
        self.defaults = {}
        
        self.buf = []
        self.shown_errors = []
        self.swmr_enabled = False
        
        if db_url is None:
            return
        
        try:
            import h5py
            self.h5py = h5py
        except Exception as e:
            logging.error(f'unable to import "h5py": {e}')
            return

        if os.path.exists(self.filepath):
            if not recreate:
                logging.error(f'file already exists: {self.filepath}: use recreate=True to overwrite')
                return
            if not os.path.isfile(self.filepath):
                logging.error(f'non-standard file already exists: {self.filepath}')
                return
            try:
                os.remove(self.filepath)
            except Exception as e:
                logging.error(f'unable to delete file: {self.filepath}: {e}')
                return
        
        try:
            self.hdf5_file = h5py.File(self.filepath, 'a', libver="latest")
        except Exception as e:
            logging.error(f'unable to open/create a HDF5 file: {self.filepath}: {e}')
            self.hdf5_file = None
            return

        if fields is not None:
            if type(fields) is dict:
                record = {}
                defaults = {}
                for k,v in fields.items():
                    if inspect.isclass(v):
                        record[k] = v()
                    else:
                        record[k] = v
                        defaults[k] = v
                self._build_dataset(record, defaults)
            else:
                logging.error(f'bad field descriptor: {fields}')

            
    def close(self):
        if self.hdf5_file is not None:
            self._flush()
            try:
                self.hdf5_file.flush()
            except:
                logging.warning(f'HDF5: Error on flushing data to disk: {e}')
            finally:
                self.hdf5_file.close()
                self.hdf5_file = None


    def another(self, dataset, fields=None):
        datastore = DataStore_HDF5(
            None, dataset, fields,
            flush_every=self.flush_every,
            chunk_rows = self.chunk_rows,
            compression = self.compression,
        )
        datastore.file_holder = self.file_holder
        datastore.h5py = getattr(self.file_holder, 'p5py', None)
        
        return datastore

        
    def _open_transaction(self):
        return self.file_holder.hdf5_file

    
    def _close_transaction(self, handler):
        pass

    
    def _write_one(self, hdf5_file, timestamp, tag, fields, values, update):
        if update is True and 'update' not in self.shown_errors:
            logging.error('HDF5: "update()" is not available for HDF5: switched to append()')
            self.shown_errors.append('update')
        
        channels = self._channels(tag, fields)
        if len(channels) != len(values):
            if 'mismatch' not in self.shown_errors:
                logging.error(f'HDF5: len(channels)={len(channels)} != len(values)={len(values)}')
                logging.info(f'HDF5:   tag: {tag}')
                logging.info(f'HDF5:   fields: {fields}')
                logging.info(f'HDF5:   values: {values}')
                self.shown_errors.append('mismatch')
            return
            
        record = {}
        for i, ch in enumerate(channels):
            record[ch] = values[i]
        if self.dataset is None:
            self._build_dataset(record)
            if self.dataset is None:
                return

        row = {}
        for name, dt in self.fields:
            if name == 'timestamp':
                row[name] = timestamp
            else:
                row[name] = record.get(name, None) or self.defaults[name]
            
        self.buf.append(row)
        if len(self.buf) >= self.flush_every:
            self._flush()


    def _build_dataset(self, first_record, defaults={}):
        if self.file_holder.hdf5_file is None:
            return

        def _dtype_and_default(name:str, value):
            if name == 'timestamp':
                return float, float('nan')
            if type(value) is float:
                return float, float('nan')
            if type(value) is int:
                return int, 0
            if isinstance(value, np.floating):
                return type(value), np.nan
            if isinstance(value, np.integer):
                return type(value), 0
            return self.h5py.string_dtype(encoding='utf-8'), ''

        self.fields = [('timestamp', np.float64)]
        self.defaults = {'timestamp': 0}
        
        for name, value in first_record.items():
            dt, dv = _dtype_and_default(name, value)
            self.fields.append((name, dt))
            if name in defaults:
                self.defaults[name] = defaults[name]
            else:
                self.defaults[name] = dv

        if len(self.fields) < 2:
            # only timestamp: wait until we see at least 1 channel
            return

        self.dataset = self.file_holder.hdf5_file.require_dataset(
            self.dataname,
            shape = (0,),
            maxshape =(None,),
            dtype = np.dtype(self.fields),
            chunks = (self.chunk_rows,),
            compression = self.compression,
        )

        if not self.file_holder.swmr_enabled:
            self.file_holder.hdf5_file.flush()
            self.file_holder.hdf5_file.swmr_mode = True  # make the file readable while writing
            self.file_holder.swmr_enabled = True
            
        
    def _flush(self):
        if self.file_holder.hdf5_file is None or self.dataset is None:
            return
        if not self.buf:
            return

        chunk_size = len(self.buf)
        block = np.empty(chunk_size, dtype=np.dtype(self.fields))
        for name, _dt in self.fields:
            block[name] = [ row[name] for row in self.buf ]
            
        old_size = int(self.dataset.shape[0])
        new_size = old_size + chunk_size
        self.dataset.resize((new_size,))
        
        self.dataset[old_size:new_size] = block

        try:
            self.file_holder.hdf5_file.flush()
        except Exception as e:
            logging.warning(f'HDF5: Error on flushing data to disk: {e}')
        finally:
            self.buf.clear()
