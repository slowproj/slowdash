---
title: Data-Source Plugin
---

# Plugin Structure
- Create `datasource_XXX.py` file under `system/plugin`, where `XXX` is the name of the datasource.
- Derive a plugin class `DataSource_XXX` from `DataSource` in `datasource.py`.
- Implement:
  - `__init__()`
  - `get_channels()`
  - `get_timeseries()`
  - `get_object()`
  - `get_blob()` (usually empty)
  - `get_dataframe()` (optional)
- `Datasource` class provides methods that can be used by plugin:
  - `resample()`


The minimal / empty class will be:
```python
from datasource import DataSource

class Datasource_XXX(Datasource):
  def __init__(self, project_config, config):
    super.__init__(project_config, config)

  def get_channels(self):
    return []
    
  def get_timeseries(self, channels, length, to, resampling=None, reducer='last'):
    return {}

  def get_object(self, channels, length, to):
    return {}
    
  def get_blob(self, channel, params, output):
    return None
```

# Method Definitions
### User Function `__init___`
```python
  def __init__(self, project_config, config):
    super.__init__(project_config, config)
    ...
```

### User Function `get_channels()`
- return a list of channels
```python
  def get_channels(self):
    result = []
    ...
    return result
```
- Return in JSON or string: `[ {"name": NAME, "type": TYPE, ...}, ... ]`
- `type` is one of: `timeseries`, `histogram`, `table`, and `tree`


### Optional User Function `get_timeseries()`
- return time-series data
```python
  def get_timeseries(self, channels, length, to, resampling=None, reducer='last'):
    result = {}
    ...
    return result
```
- Return in JSON or string, format as defined in the `DataModel.md` document
- If `resampling` is not None, apply resampling. 
  - If `resampling <= 0`, just align data points among channels with inferring the intervals from data.
  - `reducer` can be: 
    - `first`: value of the first non-NaN data point
    - `last`: value of the last non-NaN data point
    - `mean`: mean of non-NaN data point values
    - `median`: median of non-NaN data point values
    - `sum`: sum of non-NaN data point values
    - `count`: number of non-NaN data point values
    - `std`: standard deviation of non-NaN data point values
    - `min`: minimum data point value
    - `max`: maximum data point value
  - If resampling is not supported by the data source, use `self.resample()`.


### Optional User Function `get_object()`
- return object time-series, or single object
```python
  def get_object(self, channels, length, to):
    result = {}
    ...
    return result
```
- Return in JSON or string, format as defined in the `DataModel.md` document
    

### Optional User Function `get_blob()`
- Fill blob content
```python
  def get_blob(self, channel, params, output):
    ...
    return mime_type
```
- Fill the blob content into "output" and return the mime_type
    

### Optional User Function `get_dataframe()`
- return time-aligned time-series data table
- implement this only if datasource can do this efficiently
```python
def get_dataframe(self, channels, length, to, resampling=None, reducer='last', timezone='local'):
    result = []
    ...
    return result
```
- The parameters are same as `get_timeseries()`    
- Return in JSON or CSV text

The JSON format is
```json
[
  ["DateTime", "TimeStamp", CH0, CH1, ... ],
  RAW[0],
  RAW[1],
  ...
]
```
where `RAW[k]` is:
```json
[ DATETIME[k], TIMESTAMP[k], X0[k], X1[k], ... ]
```


### Utility Function for Users `resample()`
```python
def resample(self, set_of_timeseries, length, to, interval, reducer):
    return RESAMPLED_TIME_SERIES
```
This will be used in user's `get_timeseries()`, if the data source does not efficiently support resampling, typically like:
```python
class DataSource_XXX(DataSource):
    def get_timeseries(self, channels, length, to, resampling=None, reducer='last'):
        result = {}
        ...

        if resampling is None:
            return result
            
        return self.resample(result, length, to, resampling, reducer)
```
