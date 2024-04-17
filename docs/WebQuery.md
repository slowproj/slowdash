---
title: Web Query
---

# URL Parameters
## SlowPlot
### URL
#### Case 1: Start from blank
```http
http://ADDRESS:PORT/slowplot.html?OPTIONS
```

#### Case 2: Making a plot of (a) specified channel(s)
```
http://ADDRESS:PORT/slowplot.html?channel=CHANNELS&OPTIONS
```

- CHANNELS is a list of channels separated by `,` without spaces.
- To make multiple plots, separate the channels by `;`.
- Plots can have type specifier, separated by `/`. Default is "timeseries".
- Example: `channel=ch0,ch1;log/table`.

#### Case 3: Using saved configuration file
```
http://ADDRESS:PORT/slowplot.html?config=CONFIG_FILE&OPTIONS
```

### Mandatory Options
- For Case 2: `channel=CAHNNEL_LIST`
- For Case 3: `config=CONFIG_FILE`

### Optional Options
- `to=TIME` (in UNIX time or ISO format, default: current time)
- `length=LENGTH` (default: 900)
- `reload=RELOAD` (default: 300)
- `grid=GRID` (default: 2x1)


## SlowDash
### URL
```
http://ADDRESS:PORT/slowdash.html?config=CONFIG_FILE&OPTIONS
```
### Mandatory Options
- `config=CONFIG_FILE`

### Optional Options
- `time=TIME` (in UNIX time or ISO format, default: current time)
- `length=LENGTH` (default: 3600)
- `reload=RELOAD` (default: 300)

## SlowCruise
### URL
```
http://ADDRESS:PORT/slowcruise.html?config=CONFIG_FILE&OPTIONS
```

### Mandatory Options
- `config=CONFIG_FILE`

### Optional Options
- `interval=INTERVAL` (default: 60)



# Web API

## Ping
### Request
```
GET http://ADDRESS:PORT/api/ping
```
### Reply
```json
"pong"
```

## Echo Request
### Request
```
GET http://ADDRESS:PORT/api/echo/PATH?OPTIONS
```
### Reply
```json
{
    "URL": "echo/PATH?OPTIONS",
    "Path": [ PATH_ELEMENTS ],
    "Opts": { OPTION_ELEMENTS }
}
```

## Getting Project Configuration
### Request
```
GET http://ADDRESS:PORT/api/config
```

### Reply Example (ATDS Project)
```json
{
    "project": {
        "name": "ATDS",
        "title": "Atomic Tritium Demonstrator at UW (ATDS)"
    },
    "style": {
        "theme": "light"
    },
    "contents": {
        "slowdash": [
            {
                "name": "ATDS",
                "mtime": 1677724206.5829866,
                "title": "",
                "description": "Atomic Tritium Demonstrator at UW Top Level",
                "config_file": "slowdash-ATDS.json"
            }
        ],
        "slowplot": [
            {
                "name": "RTD_ACC",
                "mtime": 1678019620.6981564,
                "title": "Accomodator RTDs",
                "description": "Accomodator RTDs",
                "config_file": "slowplot-RTD_ACC.json"
            },
            {
                "name": "ATDS",
                "mtime": 1677726950.1148098,
                "title": "ATDS Overview",
                "description": "ATDS Standard Plots",
                "config_file": "slowplot-ATDS.json"
            }
        ],
        "slowcruise": [
            {
                "name": "AllPlots",
                "mtime": 1678019441.923559,
                "title": "ATDS All Plots",
                "description": "Loop over all Dashboards and Plots",
                "config_file": "slowcruise-AllPlots.yaml"
            }
        ],
        "alarms": [
            {
                "name": "normal",
                "mtime": 1630663955.5648437,
                "title": "",
                "description": "",
                "config_file": "alarms-normal.yaml"
            }
        ]
    }
}
```

## Channel List Query
### Request
```
GET http://ADDRESS:PORT/api/channels
```
### Reply
```json
[
    { "name": CH0_NAME, "type": CH0_TYPE },
    ...
]
```

## Data Query
### Request
```
GET http://ADDRESS:PORT/api/data/CHANNEL_LIST?OPTIONS
```
channel list is:
```
CH0,CH1,CH2...
```
options are:

```
length=LENGTH [default 3600]
to=TO [default 0 (now)]
resample=RESAMPLE [default 0 (auto)]
reducer=REDUCER [default "last"]
```

For details see the [Data Model section](DataModel.html).

## Fetching Blob Data Content
### Request
```
GET http://ADDRESS:PORT/api/blob/CHANNEL/ID
```

## Listing User Configuration Entries
### Request
```
GET http://ADDRESS:PORT/api/config/list
```

## Listing User Configuration Files
### Request
```
GET http://ADDRESS:PORT/api/config/filelist
```

## Fetching User Configuration Files
### Request
```
GET http://ADDRESS:PORT/api/config/file/FILENAME
```

- The FILENAME must:
  - start with an alphabet or `_`
  - consist of only alphabets, digits, `_`, `-`, `.`, `,`, `:`, `[` and `]`
  - end with one of: `.json`, `.yaml`, `.html`, `.png`, `.jpg`, `.jpeg`, `.svg`, `.csv`


## Uploading User Configuration Files
### Request
```
POST http://ADDRESS:PORT/api/config/file/NAME?OPTIONS
[ with JSON text as contents ]
```
- The NAME must:
  - consist of only alphabets, digits, `.`, `_` and `-`.
  - start with `slowdash-`, `slowplot-`, or `slowcruise-`.
  - end with `.json` or `.yaml`.
- Files are stored under the `config` sub-directory of the user project directory.

### Response
- If the file writing is not permitted by the file system,
    - returns the HTTP response code 403 (Forbidden).
- If the file already exists, and OPTION does not include `overwrite=yes`,
    - returns the HTTP response code 202 (Accepted) without overwriting.
- Otherwise, the file will be created or overwritten, and
    - if writing is successful, returns HTTP response 201 (Created).
    - otherwise returns HTTP response 500 (Internal Server Error).


### JavaScript Snippet
```javascript
fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
    body: JSON.stringify(doc, null, 2)
})
.then(response => {
    if (response.status == 202) {
       // file already exists. retry with overwrite=yes to overwrite
       return;
    }
    if (! response.ok) {
        throw new Error(response.status + " " + response.statusText);
    }
    //// success ////
    ....
})
.catch(e => {
    //// error  ////
    ....
});
```


## Sending Commands to User Modules
### Request
```
POST http://ADDRESS:PORT/api/control
[ with JSON text as contents ]
```

### Response
- If the command is not recognized, returns the HTTP response 400 (Bad Request).
- If the command is processed, returns the HTTP response 201, with contents of:
  - If the user module provides custom result JSON (typically with `{"status": ...; "message": ...}`), it will be returned.
  - Otherwise, returns `{"status": "ok"}` on success, or  `{"status": "error"}` on error.

### JavaScript Snippet
A typical JavaScript would look like:
```javascript
fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
    body: JSON.stringify(doc, null, 2)
})
.then(response => {
    if (! response.ok) {
        throw new Error(response.status + " " + response.statusText);
    }
    return response.json();
})
.then(doc => {
    if ((doc.status ?? '').toUpperCase() == 'ERROR') {
        throw new Error(doc.message ?? '');
    }
    //// success ////
    ....
})
.catch(e => {
    //// error ////
    ....
});
```
