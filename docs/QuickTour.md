---
title: Quick Tour
---

# Course Overview
In this tour we will use SQLite for data backend which does not require server setup. All the files created during the tour are confined under a project directory, and can be removed completely and safely by just deleting the directory.

### Menu
- Configuring a project, with describing the user data schema
- Running Slow-Dash
- Creating several plots on a Web-browser
- Running user code on the server-side
- Sending commands to the user code

### First thing first
To get started, prepare a place:
```console
$ mkdir QuickTour
$ cd QuickTour
```

### Using Docker?
The directory just created will be mapped into the container as a volume. You can work either inside the container (by `docker exec ...  /bin/bash` or outside, but working outside should be easier.

# Test-Data Generation
Download the test data generation script <a href="generate-testdata.py.txt" download="generate-testdata.py">generate-testdata.py</a>, or get it from `PATH/TO/SLOWDASH/ExampleProjects/QuickTour/generate-testdata.py`, and place it at the project directory.

```console
$ mv PATH/TO/DOWNLOAD/generate-testdata.py .
OR
$ cp PATH/TO/SLOWDASH/ExampleProjects/QuickTour/generate-testdata.py .
```

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
CREATE TABLE testdata(datetime DATETIME, timestamp INTEGER, channel STRING, value REAL, PRIMARY KEY(timestamp, channel));
sqlite> select * from testdata limit 10;
2023-04-11 23:52:13|1681257133|ch00|0.187859
2023-04-11 23:52:13|1681257133|ch01|-0.418021
2023-04-11 23:52:13|1681257133|ch02|0.482607
2023-04-11 23:52:13|1681257133|ch03|1.733749
...
```

As shown above, the schema of the data table is:
```
testdata(datetime DATETIME, timestamp INTEGER, channel STRING, value REAL, PRIMARY KEY(timestamp, channel))
```

and the table contents are:

|datetime (DATETIME/STRING)|timestamp (INTEGER)|channel (STRING)|value (REAL)|
|----|-----|-----|-----|
|2023-04-11 23:52:13|1681257133|ch00|0.187859|
|2023-04-11 23:52:13|1681257133|ch01|-0.418021|
|2023-04-11 23:52:13|1681257133|ch02|0.482607|
|2023-04-11 23:52:13|1681257133|ch03|1.733749|
|...||||

(In SQLite, DATETIME is STRING. Here the time-zone is UTC although it is not specified explicitly.)

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
    type: SQLite
    parameters:
      file: QuickTourTestData.db
      time_series:
          schema: testdata[channel]@timestamp(unix)=value
```

To use the `datetime` column for the timestamps, the schema part of the configuration file would look like this:
```yaml
      time_series:
          schema: testdata[channel]@datetime(unspecified utc)=value
```
The timestamp type is indicated after the time column name. Other common values of timestamp type are: `aware` (or `with time zone`) for time data with explicit time zone, and `naive` (or `without time zone` or `local`) for implied "local" time zone (often a bad idea). The `unspecified utc` is a special one that the time data does not have explicit time zone, which looks like "local", but the times are actually in UTC.

### Testing the Configuration (Bare-Metal installation only)

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
### Step 1 
#### Docker
```console
$ docker-compose up
```
This will start a SlowDash server and open a port at 18881. To stop it, type `ctrl`-`c` on the terminal, or run `docker-compose stop` (or `down`)
if you started `docker-compose` with the `-d` option.

#### Bare-Metal
Launch the server, with an arbitrary port number. Leave this command running while testing.
```console
$ slowdash --port=18881
```
### Step 2
Launch a web browser, access to `http://localhost:18881`.
```console
$ firefox http://localhost:18881
```
The browser should show the home page of the project:

<img src="fig/QuickTour-Home.png" style="width:40%">

### Step 3: Only for this quick tour
In order to continuously fill the data while plotting, run the test-data generator in parallel (maybe in another terminal window):
```console
$ python3 generate-testdata.py
```
The data file size is roughly 5 MB per hour. The test data file, `QuickTourTestData.db`, can be deleted safely when SlowDash is not running.
Once the file is deleted, run `generate-testdata.py` again before starting Slow-Dash next time.

## Making Plots
### Time-series Plot
Probably just playing with the GUI would be easier than reading this section...

- Click one of the channels in the "Channel List" panel to make a time-series  plot of the channel.
- Or, click "Blank" or "Blank 2x2" in the "Slow-Plot" panel to start a new empty layout.
<p>
- Putting mouse pointer on blank space will show a "Add New Panel" button. Click it and then select "Time-Axis Plot" to make a new plot.
- Putting mouse pointer on a plot shows a set of control buttons. Click the &#x1f6e0; button to configure the plot axes and styles, and to add a new time-series.

### Histogram
### Dashboard Canvas
### Table View
### Map View

## Configuration by URL
### Panel Building from URL
#### By configuration file
```
http://localhost:18881/slowplot.html?config=slowplot-QuickTour.json&time=2023-03-30T18:00:00&reload=0
```

#### By channels and plot types
```
http://localhost:18881/slowplot.html?channel=ch00;ch00/ts-histogram&length=360&reload=60&grid=2x1
```

#### Useful parameters


### Auto-Cruise

# Advanced Usage
## Data Transform
## User Module
## Sending Commands
