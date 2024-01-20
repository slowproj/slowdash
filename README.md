# SlowDash
Web tool for control and monitoring of concurrent systems (slow-controls and data-acquisition)

## Screenshots
### Dashboard
<img src="https://slowproj.github.io/slowdash/fig/Top-Canvas.png" width="70%">

### Interactive Plots
<img src="https://slowproj.github.io/slowdash/fig/Top-PlotTypes.png" width="70%">

## Setup and Quick Look
- prerequisite for this: Python3 (>=3.8), python3-numpy, python3-psutil

The procedure below will create a new directory, `slowdash`. 
Everything is fully contained under this directory, and nothing in your system is modified except for the directory.
```
git clone https://github.com/slowproj/slowdash.git --recurse-submodules
cd slowdash/system; make
cd ..; source bin/slowdash-bashrc
cd ExampleProjects/DummyDataSource
slowdash --port=18881
```
then open a web browser and connect to `http://localhost:18881`.
To stop, type `ctrl`-`c`.

## Documentation
see [Github Pages](https://slowproj.github.io/slowdash/)
