# SlowDash
Web tool for control and monitoring of concurrent systems (slow-controls and data-acquisition), primarily designed for physics experiments

#### Project Goal
- Grafana-like data browser for ROOT-like data objects (graphs, histograms, etc.)
- LabVIEW-like visual control (graphical control panel)
- Jupyter-like interactive scripting with Python

#### Current Status
- Data browser mostly working
- Controls partly implemented
- Analysis part (scripting etc.) is experimental

## Screenshots
### Dashboard
<img src="https://slowproj.github.io/slowdash/fig/Top-Canvas.png" width="70%">

### Interactive Plots
<img src="https://slowproj.github.io/slowdash/fig/Top-PlotTypes.png" width="70%">

## Setup and Quick Look
##### Prerequisite for this trial
- Git
- Python3 (>=3.8) and packages:
  - numpy
  - psutil

The procedure below will create a new directory, `slowdash`. 
Everything is fully contained under this directory, and nothing in your system (other than this directory) will be modified through this trial.

##### Step 1: Clone with submodules
```
git clone https://github.com/slowproj/slowdash.git --recurse-submodules
```

##### Step 2: Setup
```
cd slowdash/system; make
cd ..; source bin/slowdash-bashrc
```
Here `make` is used only to copy some files within the `slowdash` directory. If submodules are missing, `make` will also run `git submodule update --init --recursive`.

##### Step 3: Start an example project
```
cd ExampleProjects/DummyDataSource
slowdash --port=18881
```

##### Step 4: Take a look with a browser
Open a web browser and connect to `http://localhost:18881`.
To stop, type `ctrl`-`c` in the slowdash console in Step 3.


## Documentation
see [Github Pages](https://slowproj.github.io/slowdash/)
