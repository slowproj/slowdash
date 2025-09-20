# Created by Sanshiro Enomoto on 19 September 2025 #


import logging
from .store import DataStore


class DataStore_HDF5(DataStore):
    def __init__(self, db_url:str, dataset:str, *, flush_every=128, chunk_rows=8192, compression='lzf'):
        '''Writes time-series data to a HDF5 file in a wide format using NumPy compounds
        Parameters:
          - db_url: path to the HDF5 file. Example: 'hdf5:///SlowStore.h5'
          - dataset: HDF "dataset" name
        Notes:
          - Field names and types are inferred from the first record
          - `anoter(dataset)` makes another dataset in the same HDF5 file
          - The HDF5 file are readable by multiple processes while writing (SWMR mode)
          - Available compressions are:
            - lzf: fast
            - gzip: more compression, slower
        '''
        
        self.filepath = self.db_url[8:] if self.db_url.startswith('hdf5://') else self.db_url
        self.dataname = str(dataset) or 'SlowData'
        self.flush_every = flush_every
        self.chunk_rows = chunk_rows
        self.compression = compression
        
        self.hdf5_file = None
        self.file_holder = self
        self.buf = []
        self.shown_errors = []
        if db_url is None:
            return
        
        try:
            import h5py
        except:
            logging.error('unable to import "h5py"')
            return
        self.h5_str_type = h5py.string_dtype(encoding='utf-8')
        
        try:
            self.hdf5_file = h5py.File(self.filepath, 'w', libver="latest")
        except Exception as e:
            logging.error(f'unable to create a HDF5 file: {filename}: {e}')
            self.hdf5_file = None

        if self.hdf5_file is not None:
            self.hdf5_file.swmr_mode = True  # make the file readable while writing
            
            
    def __del__(self):
        self.close()


    def close(self):
        if self.hdf5_file is not None:
            self._flush()
            self.hdf5_file.close()
            self.hdf5_file = None


    def another(self, dataset):
        datastore = DataStore_HDF5(None, dataset)
        datastore.file_holder = self
        
        return datastore

        
    def _open_transaction(self):
        return self.file_holder.hdf5_file

    
    def _close_transaction(self, redis):
        pass

    
    def _write_one(self, hdf5_file, timestamp, tag, fields, values, update):
        if update is True and 'update' not in self.shown_errors:
            logging.error('HDF5: "update()" is not available for HDF5: switched to append()')
            self.shown_errors.append('update')
        
        channels = self._channels(tag, fields)
        if len(channels) != len(values):
            if 'mismatch' not in self.shown_errors:
                logging.error('inconsistent lengths between tag/fields and values')
                self.shown_errors.append('mismatch')
                return
            
        record = { 'timestamp': np.float64(timestamp) }
        for i in range(len(channels)):
            record[channels[i]] = values[i]
        if self.dataset is None:
            self._build_dataset(record)
        if self.dataset is None:
            return

        data = {}
        for name, dt in self.fields:
            data[name] = record.get(name, None) or self.defaults[name]
            
        self.buf.append(data)
        if len(self.buf) >= self.flush_every:
            self._flush()


    def _build_dataset(self, record):
        self.fields = []
        self.defaults = {}
        
        for name, value in record.items():
            datatype = type(value)
            if datatype is int:
                datatype = np.int32
            elif datatype is float64:
                datatype = np.int
            elif datatype is str:
                datatype = self.h5_str_type
                
            dt = np.dtype(datatype)
            if dt.kind in "f":
                self.defaults[name] = np.nan
            elif dt.kind in "iu":
                self.defaults[name] = 0
            else:
                self.defaults[name] = ''

            self.fields.append((name, datatype))

        if len(self.fields) < 2: # 1 for timestamp
            return
            
        self.dataset = self.file_holer.hdf5_file.require_dataset(
            self.dataname,
            shape = (0,),
            maxshape =(None,),
            dtype = np.dtype(self.fields),
            chunks = (self.chunk_rows,),
            compression = self.compression
        )

        
    def _flush(self):
        if self.file_holder.hdf5_file is None:
            return
        if len(self.buf) == 0:
            return

        chunk_size = len(self.buf)
        old_size = self.dataset.shape[0]
        new_size = old_size + chunk_size
        self.dataset.resize((new_size,))
        chunk = np.empty(chunk_size, dtype=np.dtype(self.fields))
        for i, record in enumerate(self.buf):
            chunk[i] = record
        self.dataset[old_size:new_size] = chunk
        
        try:
            self.dataset.flush()
        except:
            pass
        self.file_holder.hdf5_file.flush()
        
        self.buf.clear()
