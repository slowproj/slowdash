
# TODO:
#   If the input dataset is not a compound but contains multiple (sub)datasets,
#   zip the arrays to create a CSV.


import os, csv, h5py


def hdf5_to_csv(input_filepath:str, dataset_name:str):
    """Extracts table data from HDF5 input file and creates a CSV file
    Parameters:
      - input_filepath (str): path to the HDF5 file
      - dataset_name (str): name of the dataset
    Notes:
      - This assumes that the dataset is a numpy compound,
        otherwise a single array is taken from the dataset and written to the output CSV
      - If dataset_name is not given, the first compound dataset is taken.
        If compound dataset does not exist, the first dataset is taken.
    """

    output_filepath = os.path.splitext(input_filepath)[0] + '.csv'

    with h5py.File(input_filepath, 'r') as hdf5:
        print(f'Input File: {input_filepath}')
        if len(hdf5) < 1:
            print(f'file empty')
            return None

        if dataset_name is None:
            first_name = None
            for name in hdf5:
                obj = hdf5[name]
                if not isinstance(obj, h5py.Dataset):
                    continue
                if first_name is None:
                    first_name = name
                if obj.dtype.name is not None:
                    dataset_name = name
                    break
            else:
                dataset_name = first_name
        print(f'Dataset Name: {dataset_name}')
        
        try:
            ds = hdf5[dataset_name]
        
            print(f'Rows: {len(ds)}')
            if ds.dtype.names is not None:
                print(f'Columns: {', '.join([f'{name} ({v[0]})' for name, v in ds.dtype.fields.items()])}')
            else:
                print(f'Columns: {dataset_name}')

            with open(output_filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(ds.dtype.names or dataset_name)
                for row in ds:
                    writer.writerow(row)
            print(f'Output File: {output_filepath}')
        except Exception as e:
            print(f'ERROR: {e}')
            return None

        return output_filepath


    
if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument(
        'HDF5_FILE',
        help='Input HDF5 file path'
    )
    parser.add_argument(
        'DATASET', nargs='?',
        help='Dataset name (expects a compound); Default is the first (compound) dataset'
    )
    parser.add_argument(
        '--tail=N',
        action='store', dest='tail', type=int, default=3,
        help='dumps the tail N lines of the output after successful conversion'
    )
    args = parser.parse_args()

    csv_file = hdf5_to_csv(args.HDF5_FILE, args.DATASET)

    if csv_file is not None and args.tail > 0:
        import subprocess
        subprocess.run(f'head -n 1 {csv_file}', shell=True)
        subprocess.run(f'tail -n {args.tail} {csv_file}', shell=True)
