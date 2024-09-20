---
title: Quick Tour
---

# Course Overview
In this tour we will use SQLite for data backend which does not require server setup. All the files created during the tour are confined under a project directory, and can be removed completely and safely by just deleting the directory.

### Menu
- Configuring a project, with describing the user data schema
- Running Slow-Dash
- Creating several plots on a Web-browser
- ~~Running user code on the server-side~~ (preparing)
- ~~Sending commands to the user code~~ (preparing)

### First thing first
To get started, prepare a place:
```console
$ mkdir QuickTour
$ cd QuickTour
```

### Using Docker?
The directory just created will be mapped into the container as a volume. You can work either inside the container (by `docker exec ...  /bin/bash`) or outside, but working outside should be easier in the beginning.

# Test-Data Generation
To generate test-data, we use the SlowPy Python library that comes with the SlowDash package. Write the code below and save it as `generate-testdata.py` at your project directory:
```python
import slowpy.control
import slowpy.store


class TestDataFormat(slowpy.store.LongTableFormat):
    schema_numeric = '(datetime DATETIME, timestamp INTEGER, channel STRING, value REAL, PRIMARY KEY(timestamp, channel))'
    def insert_numeric_data(self, cur, timestamp, channel, value):
        cur.execute(f'INSERT INTO {self.table} VALUES(CURRENT_TIMESTAMP,{int(timestamp)},?,{float(value)})', (str(channel),))


ctrl = slowpy.control.ControlSystem()
device = slowpy.control.RandomWalkDevice(n=4)
datastore = slowpy.store.DataStore_SQLite('sqlite:///QuickTourTestData.db', table="testdata", table_format=TestDataFormat())


def _loop():
    for ch in range(4):
        data = device.read(ch)
        datastore.append(data, tag="ch%02d"%ch)
    ctrl.sleep(1)
    

def _finalize():
    datastore.close()
    
    
if __name__ == '__main__':
    ctrl.stop_by_signal()
    while not ctrl.is_stop_requested():
        _loop()
    _finalize()
```
Details of the script is described in the [Controls](ControlsScript.html) section. For now just copy-and-past the script and use it to generate some test-data.

Running this script will create a SQLite database file and fill it with dummy time-series data every second.
```console
$ python3 generate-testdata.py
```

Stop the script by <kbd>ctrl</kbd>-<kbd>C</kbd> after a minute and look at the created file:
```console
$ ls -l
-rw-r--r-- 1 sanshiro sanshiro 24576 Apr 11 16:52 QuickTourTestData.db
-rwxr-xr-x 1 sanshiro sanshiro  3562 Apr 11 16:51 generate-testdata.py
```

The contents can be viewed with the SQLite command-line program, `sqlite3`. If this program is not available on your system, just skip this step; you will see the contents with Slow-Dash in the next step.
```console
$ sqlite3 QuickTourTestData.db 
SQLite version 3.31.1 2020-01-27 19:55:54
Enter ".help" for usage hints.
sqlite> .table
testdata
sqlite> .schema testdata
CREATE TABLE testdata(datetime DATETIME, timestamp INTEGER, channel TEXT, value REAL, PRIMARY KEY(timestamp, channel));
sqlite> select * from testdata limit 10;
2023-04-11 23:52:13|1681257133|ch00|0.187859
2023-04-11 23:52:13|1681257133|ch01|-0.418021
2023-04-11 23:52:13|1681257133|ch02|0.482607
2023-04-11 23:52:13|1681257133|ch03|1.733749
...
```

As shown above, the schema of the data table is:
```
testdata(datetime DATETIME, timestamp INTEGER, channel TEXT, value REAL, PRIMARY KEY(timestamp, channel))
```

and the table contents are:

|datetime (DATETIME/TEXT)|timestamp (INTEGER)|channel (TEXT)|value (REAL)|
|----|-----|-----|-----|
|2023-04-11 23:52:13|1681257133|ch00|0.187859|
|2023-04-11 23:52:13|1681257133|ch01|-0.418021|
|2023-04-11 23:52:13|1681257133|ch02|0.482607|
|2023-04-11 23:52:13|1681257133|ch03|1.733749|
|...||||

(In SQLite, DATETIME is TEXT. Here the time-zone is UTC although it is not specified explicitly.)

For demonstration purpose, this table has two timestamp columns, one for (emulated) hardware data time in the UNIX time type, and the other for database writing time in the date-time type. An actual system might have only one of them in either types.

Other forms of data tables also can be handled by Slow-Dash. See the [Data Binding section](DataBinding.html) for details.

# Basic Usage

## Project Configuration
Project configuration file describes which database to read, which column is for the time-stamps and which column is for the data values, etc. Each Slow-Dash project has one project configuration file, named `SlowdashProject.yaml`, located at the project directory.

### Writing a Configuration File

Create `SlowdashProject.yaml` with the contents below:
```yaml
slowdash_project:
  name: QuickTour
  title: Slow-Dash Quick Tour

  data_source:
    url: sqlite:///QuickTourTestData.db
    parameters:
      time_series:
        schema: testdata [channel] @timestamp(unix) = value
```

To use the `datetime` column for the timestamps, the schema part of the configuration file would look like this:
```yaml
      time_series:
          schema: testdata[channel]@datetime(unspecified utc)=value
```
The timestamp type is indicated after the time column name. Other common values of timestamp type are: `aware` (or `with time zone`) for time data with explicit time zone, and `naive` (or `without time zone` or `local`) for implied "local" time zone (often a bad idea). The `unspecified utc` is a special one that the time data does not have explicit time zone, which looks like "local", but the times are actually in UTC.

### Testing the Configuration

(If you are using Docker, first get into the container by `docker exec -it CONTAINER_ID /bin/bash`.)

To test the configuration, run the `slowdash config` command at the project directory:
```console
$ slowdash config
{
    "project": {
        "name": "QuickTour",
        "title": "Slow-Dash Quick Tour",
        "error_message": ""
    },
    "data_source": {
        "type": "SQLite",
        "parameters": {
            "file": "QuickTourTestData.db",
            "time_series": {
                "schema": "testdata[channel]@timestamp(unix)=value"
            }
        }
    },
    "style": null,
    "contents": {
        "slowdash": [],
        "slowplot": []
    }
}
```

The channels in the data-store can be listed with the `slowdash channels` command:
```console
$ slowdash channels
[
  {"name": "ch00"}, {"name": "ch01"}, {"name": "ch02"}, ...
]
```

The data values can be displayed with the `slowdash data` command:
```console
$ slowdash "data/ch00?length=10"
{
  "ch00": {
    "start": 1680223465, "length": 10, 
    "t": [0.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0], 
    "x": [5.180761, 5.92074, 5.515459, 4.883299, 5.650556, 4.284527, 3.884656, 3.223627, 2.06343]
  }
}
```

## Running
### Step 1: Starting the SlowDash Server
This step will start a SlowDash server and open a port at 18881. To stop it, type `ctrl`-`c` on the terminal.

#### Bare-Metal
```console
$ slowdash --port=18881
```

#### Docker
Image from DockerHub
```console
$ docker run --rm -p 18881:18881 -v $(pwd):/project slowproj/slowdash
```
or locally created image:
```console
$ docker run --rm -p 18881:18881 -v $(pwd):/project slowdash
```

#### Docker-Compose
Create a `docker-compose.yaml` file at the project directory
```yaml
version: '3'

services:
  slowdash:
    image: slowproj/slowdash
    volumes:
      - .:/project
    ports:
      - "18881:18881"
```

Then start `docker-compose`
```console
$ docker-compose up
```


### Step 2: Opening a Web Browser
Launch a web browser, access to `http://localhost:18881`.
```console
$ firefox http://localhost:18881
```
The browser should show the home page of the project:

<img src="fig/QuickTour-Home.png" style="width:40%">


### Step 3: Start Generating Testdata (only for this quick tour)
In order to continuously fill the data while plotting, run the test-data generator in parallel (maybe in another terminal window):
```console
$ python3 generate-testdata.py
```
The data file size is roughly 5 MB per hour. The test data file, `QuickTourTestData.db`, can be deleted safely when SlowDash is not running.
Once the file is deleted, run `generate-testdata.py` again before starting Slow-Dash next time.



## Making Plots
### Interactive Building
Probably just playing with the GUI would be easier than reading this section...

- Click one of the channels in the "Channel List" panel to make a time-series  plot of the channel.
- Or, click "New Plot Layout" in the "Tools" panel to start a new empty layout.
<p>
- Putting mouse pointer on blank space will show a "Add New Panel" button. Click it and then select "Time-Axis Plot" to make a new plot.
- Putting mouse pointer on a plot shows a set of control buttons. Click the &#x1f6e0; button to configure the plot axes and styles, and to add a new time-series.
  
So far we have only time-series data in the test database, so only time-series plots can be created at the moment.

### Saving
Created plots (called SlowPlot Layout) can be saved and shared. Click the &#x1f4be; button on the top right corner.
Saved layouts are listed in the SlowDash home page.

### Panel Building from URL
#### By configuration file
A URL can be used to open a saved layout with a specified time range:
```
http://localhost:18881/slowplot.html?config=slowplot-QuickTour.json&time=2023-03-30T18:00:00&reload=0
```

#### By channels and plot types
A layout can be created by URL only, with specifying the channel(s) and time range:
```
http://localhost:18881/slowplot.html?channel=ch00;ch00/ts-histogram&length=360&reload=60&grid=2x1
```

