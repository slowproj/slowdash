import os, csv, h5py

input_filepath = 'TestData.h5'
output_filepath = os.path.splitext(input_filepath)[0] + '.csv'
dataset_name = 'test'    # this assumes that the dataset is a numpy compound; otherwise extracts an array

with h5py.File(input_filepath, 'r') as hdf5:
    ds = hdf5[dataset_name]
    with open(output_filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(ds.dtype.names or dataset_name)
        for row in ds:
            writer.writerow(row)
