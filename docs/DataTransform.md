---
title: "Data Transform (experimental)"
---

# Overview
### Applications
- extract columns of a table for graph plotting
- data value transforms (offset, scale, etc.)
- data reduction (last, mean, ...)
- extract a scalar value for HTML substitutions
- select columns of a table or branches of a tree for displaying
- create histogram of a table column
- calculate stats of a histogram
- decode bit flags
  
### Examples
```
# simple
Temperature->last()->format('%.2f degC')
Temperature->last()->scale(1.8)->offset(32)->format('%.2f degF')
TableData -> last() -> get("NHits") -> histogram(nbins=100,min=0,max=100)

# [TODO] with target
Table->format[column='Temperature']('$.2f degC')

# [TODO] using stack
Temperature->dropBelow(0); Pressure->dropBelow(0); ->zip()
Voltages;Voltages[Main];Voltages[Offset];->sum();->addColumn()

# [TODO] using register file
Temperature->dropBelow(0)->T; Pressure->dropBelow(0)->P; (T,P)->zip()
Voltages[Main]->Vm;Voltages[Offset]->Vo; (Vm,Vo)->sum();(Voltages,.)->addColumn()

```

# Syntax
```
DATA[ADAPTER1] -> FUNCTOR1(ARG1, ARG2, ...)[ADAPTER2] -> FUNCTOR2(...) ...
```

- Use a quotation when an identifier includes special character.
- Double quotations are replaced with single quotation on parsing (to be safe in JSON).

### Functor Chain, Stack and Register
For functors that takes multiple inputs, stack operators can be used:
```
CAHNNEL1 -> FUNCTOR1(); CHANNEL2 -> FUNCTOR2() ->...; -> FUNCTOR()
```
where `;` is an operator to push the data into stack.

As an alternative method, output can be pushed back into the data set as a new channel:
```
CH_1 -> FUNCTOR1()->CH_A; CH_2 -> FUNCTOR2() -> CH_B; CH_A -> FUNCTOR()
```

### Adapters
- Adapters takes a input data and outputs an array of copied values or array of references.
- The scalar functors and array functors need an adapter for their inputs.
<p>
- `[/]`: applies to the entire time-series
- `[/PATH]` or `[PATH]`: select a time-series field, table column, tree branch
<p>
- `[PATH(PATH2=VALUE)]`: filter
<p>
- `@`: in-place prefix
  
### Syntax Sugar
- `CHANNEL[NAME]` will be converted to `CHANNEL->get(NAME)`

# List of Functors

### Scalar Functors
- Scalar functors apply to `x[k]` for each `k`.
- Unless "in-place" designator is specified, a copy will be created.
- Default adapters are:
  - If `x[k]` is a histogram, it applies to `x[k].counts` by default.
  - If `x[k]` is a graph, it applies to `x[k].y` by default.
  - If `x[k]` is a table, a column must be specified using an adapter.
  - If `x[k]` is a tree, a matching pattern must be specified using an adapter.
<p>
- `scale():  Scalar<Number> -> Scalar<Number>`
- `offset():  Scalar<Number> -> Scalar<Number>`
- `format(fmt):  Scalar<Number> -> Scalar<String>`
- `match(val):  Scalar<String> -> Scalar<Bool>`
- `decode_bits(['aaa','bbb',...]): Scalar<Number> -> Array<String>`
- `testbit():  Scalar<Number> -> Scalar<Bool>`

### Array Functors
- Arrays are created by applying an adapter.
- To apply to `X[k]` for each `k` as an array, use a target of `[X]`.
<p>
- `includes(value:String): Array<String> -> Scaler<Bool>`
- `mean(): Array<Number> -> Scaler<Number>`  (also: `median()`, `first()`, `last()`, ...)
- `head(n): Array -> Array` (also: `tail(n)`)
- `accept_range(min, max) Array<Number> -> Array<Number>`
- `rescale(percentile=100): Array<Number> -> Array<Number>`
- `standardize(): Array<Number> -> Array<Number>`
- `delta():  Array<Number> -> Array<Number>`
- `sigma():  Array<Number> -> Array<Number>`
- `histogram(nbins, min, max):  Array<Number> -> Histogram`
      
### Time-Series Functors
- `resample(): TimeSeries -> TimeSeries`
- `align(): TimeSeries[] -> TimeSeries`
- `integrate(): TimeSeries -> TimeSeries`
- `differentiate(): TimeSeries -> TimeSeries`

### Histogram Functors
- `tabulate(columns=['bin_center', 'counts']):  Histogram -> Table`
- `stat():  Histogram -> Tree`
- `bins():  Histogram -> Tree`

### Graph Functors
- `tabulate():  Graph -> Table`
  
### Table Functors
- `get(column):  Table ->  Array`
- `select(columns, labels=[]):  Table -> Table`
- `range(column, from, to):  Table -> Table`
- `fold(tag_columns): Table -> Tree`
- `graph(columns, labels=[]):  Table -> Graph`

### Tree Functors
- `get(path):  Tree -> Scalar`
- `branch(paths, labels=[]):  Tree -> Tree`
- `rename({old:new, ...}): Tree -> Tree`
