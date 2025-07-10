---
title: Quick Tour
---

# Course Overview
This tour demonstrates how to use SlowDash with SQLite as the data backend, which requires no server setup. All files created during this tour are contained within a single project directory and can be completely removed by simply deleting that directory.

### Menu
- Configure a project by defining the user data schema
- Run SlowDash
- Create interactive plots through the web interface
- ~~Execute user code on the server-side~~ (coming soon)
- ~~Send commands to user code~~ (coming soon)

### Getting Started
First, create and navigate to a new project directory:
```console
$ mkdir QuickTour
$ cd QuickTour
```

### Docker Users
If you're using Docker, the directory you just created will be mounted as a volume in the container. You can work either inside the container (using `docker exec ... /bin/bash`) or outside. In the beginning, we recommend working outside the container.

# Test Data Generation
We'll use the SlowPy Python library, included with the SlowDash package, to generate test data. Create a file named `generate-testdata.py` in your project directory with the following code:
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

If you installed SlowPy in a virtual environment (the standard installation method), activate it using either:
```console
$ slowdash-activate-venv
```
or (if `slowdash-bashrc` hasn't been sourced):
```console
$ source PATH/TO/SLOWDASH/venv/bin/activate
```

Running this script will create a SQLite database file and populate it with simulated time-series data every second:
```console
$ python3 generate-testdata.py
```

After letting it run for about a minute, stop the script using `Ctrl`-`c`</kbd> and examine the created files:
```console
$ ls -l
-rw-r--r-- 1 sanshiro sanshiro 24576 Apr 11 16:52 QuickTourTestData.db
-rwxr-xr-x 1 sanshiro sanshiro  3562 Apr 11 16:51 generate-testdata.py
```

You can inspect the database contents using the SQLite command-line program, `sqlite3`. If this program isn't available on your system, you can skip this step and view the data through SlowDash in the next section.
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

(Note: In SQLite, DATETIME is stored as TEXT. Times are in UTC, though not explicitly specified.)

For demonstration purposes, this table includes two timestamp columns: one for (emulated) hardware data time in UNIX timestamp format, and another for database writing time in datetime format. In a real system, you might use just one of these formats.

For information about other supported data table formats, please refer to the [Data Binding section](DataBinding.html).

# Basic Usage

## Project Configuration
Each SlowDash project requires a configuration file named `SlowdashProject.yaml` in the project directory. This file specifies which database to read, which columns contain timestamps and data values, and other essential settings.

### Creating the Configuration File

Create `SlowdashProject.yaml` with the following content:
```yaml
slowdash_project:
  name: QuickTour
  title: SlowDash Quick Tour

  data_source:
    url: sqlite:///QuickTourTestData.db
    time_series:
      schema: testdata [channel] @timestamp(unix) = value
```

To use the `datetime` column for timestamps instead, modify the schema section as follows:
```yaml
      time_series:
          schema: testdata[channel]@datetime(unspecified utc)=value
```
The timestamp type is specified after the time column name. Common timestamp types include:
- `aware` (or `with time zone`): for time data with explicit time zones
- `naive` (or `without time zone` or `local`): for implied "local" time zone (generally not recommended)
- `unspecified utc`: for time data without explicit time zones but known to be in UTC

### Verifying the Configuration

(Docker users should first enter the container using `docker exec -it CONTAINER_ID /bin/bash`.)

Test your configuration using the `slowdash config` command in the project directory:
```console
$ slowdash config
{
    "project": {
        "name": "QuickTour",
        "title": "SlowDash Quick Tour",
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

## Running the Application
### Step 1: Launch the SlowDash Server
This step starts a SlowDash server on port 18881. To stop the server, press `Ctrl`-`c`.

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
Create a `docker-compose.yaml` file in the project directory
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

Then start `docker compose`
```console
$ docker compose up
```


### Step 2: Opening a Web Browser
Launch a web browser and access `http://localhost:18881`.
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
Once the file is deleted, run `generate-testdata.py` again before starting SlowDash next time.



## Creating Plots
### Interactive Plot Building
The easiest way to get started is to explore the GUI:

- Click any channel in the "Channel List" panel to create a time-series plot
- Or click "New Plot Layout" in the "Tools" panel to start with an empty layout
- Hover over empty space to reveal the "Add New Panel" button
- Click it and select "Time-Axis Plot" to create a new plot
- Hover over any plot to access control buttons
- Click the &#x1f6e0; (wrench) icon to configure axes, styles, and add new time series

Currently, only time-series plots are available since our test database contains only time-series data.

### Saving Your Work
You can save and share your plot layouts (called SlowPlot Layouts) by clicking the &#x1f4be; (save) button in the top-right corner.
Saved layouts appear on the SlowDash home page.

### Creating Panels via URL
#### Using Configuration Files
Open a saved layout with a specific time range using a URL:
```
http://localhost:18881/slowplot.html?config=slowplot-QuickTour.json&time=2023-03-30T18:00:00&reload=0
```

#### Using Channel Specifications
Create a new layout directly through a URL by specifying channels and plot types:
```
http://localhost:18881/slowplot.html?channel=ch00;ch00/ts-histogram&length=360&reload=60&grid=2x1
```

