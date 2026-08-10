import h5py
import numpy as np


def hdf5_dump(file_names: list[str]):
    for file_name in file_names:
        with h5py.File(file_name, 'r') as f:
            print(f'# file: {file_name}')
            dataset_names = list(f.keys())
            for dataset_name in dataset_names:
                print(f'# dataset: {dataset_name}')
                
                data = f[dataset_name][:]
            
                columns = data.dtype.names
                print(','.join(columns))
            
                # Looping over the rows.
                # You can also get a column data by the column name, e.g., by data['timestamp']
                for row in data:
                    # Looping over row fields.
                    # You can also access field data by name, e.g., by row['timestamp']
                    values = [ str(xk.item()) for xk in row ]
                    print(','.join(values))



if __name__ == '__main__':
    import sys
    hdf5_files = [arg for arg in sys.argv if arg.endswith('.hdf5')]
    hdf5_dump(hdf5_files)
