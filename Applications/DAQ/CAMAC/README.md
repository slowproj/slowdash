# CAMAC

CAMAC DAQ for the Hoshin CAMAC controller

### Requirements
- **camdrv2** CAMAC device driver: [https://github.com/SanshiroEnomoto/camdrv2](https://github.com/SanshiroEnomoto/camdrv2)

### Usage
#### Using the pre-built app
- Up to four “standard” modules (`F0` to read, `F9` to clear, `F22` to enable LAM), with up to 8 channels each
- Triggered by LAM from one of the four modules
- Readout using the standard `F0` function on LAM
- Data is stored in HDF5 files, one file per run

```bash
cd PATH/TO/SLOWDASH/Applications/DAQ/CAMAC
slowdash --port=18881
```
Then open a web browser and go to `http://localhost:18881`.

#### Building your own app
Use the `SlowPy CAMAC` module:

```python
from slowpy.control import control_system as ctrl
ctrl.import_control_module('CAMAC')

camac = ctrl.camac(crate=1)
module = camac.module(station=3)

while True:
    module.wait()
    
    for address in range(0, 8):
        data = module.channel(address).get()
        
    module.clear()
```

The `clear()` method uses the CAMAC standard clear function, `F9`.
If another function is needed, use:

```python
module.command(function=10).get()
```

Similarly, `wait()` uses LAM and calls `F26` at the start to enable LAM.
If other operations are needed, perform them manually with `command()`.


#### Reading the data file
The `hdf5-to-csv.py` script at `slowdash/utils` convert a HDF5 file to CSV.

Also, a simple version of a CSV converter, `hdf5-dump.py`, located at the `Applications/DAQ/CAMAC` can be used as a template to write your own analysis scripts. The outline of the script looks like:
```python
    with h5py.File(file_name, 'r') as f:
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
```


### Known issues
- Currently works only with the Hoshin CCP-USB (V2) controller and the `camdrv2` device driver.
- In the pre-built app, CAMAC settings may not load correctly after the system has been idle (start/stop unused) for a long time — typically longer than the data display time range (default: 1 hour). If this happens, set the display time range to a very long value and refresh the page from the “Reload Now” pull-down menu, or restart the SlowDash process.
