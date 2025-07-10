---
title: Data Model
---

# Concepts / Terminologies
- Each "channel" produces a series of values.
- A query is made for a set of channels for a period of time.
- Query result is a set of channel data, indexed by the channel names.
- Each channel's data consists of an array of values (i.e., series). 
- If the length of the array is one, it could be represented as a single value instead of an array.
- Every value has an associated time-stamp (which does not have to be unique).
- A value can be a "scalar" (number, string, or bool) or an "object" (histogram, table, tree, ...).


# Query Syntax and Reply Format
### Query Format
```
http://ADDRESS/data/CHANNEL_LIST?OPTIONS
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

[TODO] Each channel can have options, which override the global options:
```
CH0{length=86400,resample=300},CH1,...
```
[TODO] and functors (see below for a full list of functors):
```
CH0{length=3600}->range[x](0,1000),CH1,...
CH0->histogram(100,0,100)
```
[TODO] As in the functor scheme, multiple channels can be combined using "data stack":
```
CH0;CH1;->align()
```

### Reply Packet Format
```json
{
    CH0: {
        "start": START, "length": LENGTH,
        "t": [T0, T1, T2, ...], 
        "x": [X0, X1, X2, ...]
    },
    CH1: { 
    ...
}
```
where `x[k]` can be a scalar (simple time-series) or an object (object time-series: histogram, graph, table, tree or blob). `t[k]` is the time from `START` in seconds, or [TODO] for a series of time intervals, `{"begin": tk_begin, "end": tk_end}`.

#### Examples
##### Typical time-series of scalars
```json
CH: {
    "start": START,  "length": LENGTH,
    "t": [T0, T1, T2, ...], 
    "x": [X0, X1, X2, ...]
}
```

#### Extensions
##### Reduced to a single value
If a time-series is reduced with `last()` etc., or if the data is time-neutral or "current", the data consists of only one time point (which can be "neutral" or "current"):
```json
CH: {
    "start": START,  "length": LENGTH,
    "t": T,
    "x": X
}
```
If the data is time-neutral, the value of `T` is `0`. If the data time is "current", the value of `T` will be the time of data query.

#### Bundling
[TODO]
Instead of having multiple fields (such as `y` in addition to `x`), multiple time-series with the identical time points are indicated by the `aligned` property. This is used for:

- Multiple channels read at the same time
- Multiple channels aligned by resampling
- Vectors, e.g., (x, y, z)
- Tuples, e.g., (mean, rms, min, max, n)
- Errors, e.g., (x, x_err)

[TODO]
`zip()` and `graph()` transformers will make use of this.

##### Examples
Vectors:
```json
CH0_X: {
    "start": START, "length": LENGTH,
    "aligned": ["CH0_Y", "CH0_Z"],
    "t": [T0, T1, T2, ...], 
    "x": [X0, X1, X2, ...],
}
```

Errors:
```json
CH0: {
    "start": START, "length": LENGTH,
    "aligned": ["CH0_Error"],
    "t": [T0, T1, T2, ...], 
    "x": [X0, X1, X2, ...],
}
```

Tuples:
```json
CH0_Mean: {
    "start": START, "length": LENGTH,
    "aligned": ["CH0_N", "CH0_RMS", "CH0_MIN", "CH0_MAX"]
    "t": [T0, T1, T2, ...], 
    "x": [X0, X1, X2, ...],
}
```

# Value Types and JSON Representation
### Scalar
```json
X
```
- `X` can be a number, string, bool, or `null`.

### Histogram
```json
{ 
    "bins": { "min": MIN, "max": MAX }, 
    "counts": [ C0, C1, C2, ... ] 
}
```
- Having `bins` identifies the object as a Histogram.
- Number-of-bins is the length of the `counts` array.

### 2D Histogram
```json
{ 
    "xbins": { "min": MIN, "max": MAX }, 
    "ybins": { "min": MIN, "max": MAX }, 
    "counts": [
        [ C00, C01, C02, ... ],
        [ C10, C11, C12, ... ],
        ...
    ]
}
```
- Having `ybins` identifies the object as a 2D Histogram.
- Number-of-bins is the length of the `counts` array.

### Graph
```json
{ 
    "labels": [ XLABEL, YLABEL, ZLABEL ],
    "x": [ x0, x1, x2, ... ],
    "y": [ y0, y1, y2, ... ],    
    "z": [ z0, z1, z2, ... ],
    "x_err": [ ex0, ex1, ex2, ... ],
    "y_err": [ ey0, ey1, ey2, ... ],
    "z_err": [ ez0, ez1, ez2, ... ]
}
```
- Having `y` identifies the object as a Graph.
- All the other fields are optional.
- If `x` does not exist, it will be filled with `[0:len(y)]`.

### Table
```json
{
    "columns": [COLUMN0, COLUMN1, ...], 
    "table": [
        [ X00, X01, ...], 
        [ X10, X11, ...], 
        ...
    ],
    "attr": [
        [ A00, A01, ...], 
        [ A10, A11, ...], 
        ...
    ]
}
```
- Having `table` identifies the object as a Table.
- `columns` is optional.
- `attr` is optional. `Axx` are JSON objects.
  - Defined attributes are: `color`, `background`, `href`
- [TODO] `row_attr` and `column_attr`???
  

### Tree
```json
{
    "tree": {...},
    "attr": {...}
}
```
- Having `tree` identifies the object as a Tree.
- `attr` is optional. The tree structure of `attr` corresponds to `tree`, with values by JSON.
  - Defined attributes are: `color`, `background`, `href`
  
### Blob
```json
{
    "mime": MIME_TYPE,
    "id": ID,
    "meta": META_INFO
}
```
- Having `mime` identifies the object as a Blob.
- The `id` is required. Others are optional.
