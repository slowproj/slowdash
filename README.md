# SlowDash
SlowDash is a web tool for control and monitoring of concurrent systems (slow-controls and data-acquisition), originally designed for physics experiments.

#### Project Goal
- Grafana-like data browser for time-series data and ROOT-like data objects (graphs, histograms, etc.)
- LabVIEW-like visual control (graphical control panel)
- Jupyter-like interactive scripting with Python

#### Current Status: ~60% of the initial design implemented
- Data browser mostly working
- Controls partly implemented
- Analysis part (scripting etc.) is experimental


## Screenshots
### Dashboard
<img src="https://slowproj.github.io/slowdash/fig/Gallery-ATDS-Dashboard.png" width="70%">

### Interactive Plots
<img src="https://slowproj.github.io/slowdash/fig/Gallery-PlotDemo.png" width="70%">

## Setup and Quick Look
### Docker (amd64-linux)
<details>

#### Prerequisite for this trial
- Git
- Docker & Docker Compose

#### Step 1: Clone (for example projects)
```
git clone https://github.com/slowproj/slowdash.git
```

#### Step 2: Setup
none

#### Step 3: Start an example project
```
cd slowdash/ExampleProjects/DummyDataSource
docker-compose up
```

#### Step 4: Take a look with a browser
Open a web browser and connect to `http://localhost:18881`.
To stop, type `ctrl`-`c` in the docker-composite window, or use `docker-composite stop` (or `down` to remove the container)
</details>
  
### Docker on Windows, Raspberry-Pi, etc.
<details>

#### Prerequisite for this trial
- Git
- Docker & Docker Compose

#### Step 1: Clone with submodules
```
git clone https://github.com/slowproj/slowdash.git --recurse-submodules
```

#### Step 2: Setup
```
cd slowdash
docker build -t slowdash .
```

#### Step 3: Start an example project
```
cd slowdash/ExampleProjects/DummyDataSource
```
Edit `docker-compose.yaml` to change `image: slowproj/slowdash:2401` to `image: slowdash`
```
docker-compose up
```

#### Step 4: Take a look with a browser
Open a web browser and connect to `http://localhost:18881`.
To stop, type `ctrl`-`c` in the docker-composite window, or use `docker-composite stop` (or `down` to remove the container)
</details>
  
### Bare-Metal
<details>
  
#### Prerequisite for this trial
- Git
- Python3 (>=3.8) and packages:
  - numpy, pyyaml, psutil

The procedure below will create a new directory, `slowdash`. 
Everything is fully contained under this directory, and nothing in your system (other than this directory) will be modified through this trial.

#### Step 1: Clone with submodules
```
git clone https://github.com/slowproj/slowdash.git --recurse-submodules
```

#### Step 2: Setup
```
cd slowdash/system; make
cd ..; source bin/slowdash-bashrc
```
Here `make` is used only to copy some files within the `slowdash` directory. If submodules are missing, `make` will also run `git submodule update --init --recursive`.

#### Step 3: Start an example project
```
cd ExampleProjects/DummyDataSource
slowdash --port=18881
```

#### Step 4: Take a look with a browser
Open a web browser and connect to `http://localhost:18881`.
To stop, type `ctrl`-`c` in the slowdash console in Step 3.

</details>

## Documentation
See [Github Pages](https://slowproj.github.io/slowdash/).

For status and updates, see [GitHub Wiki](https://github.com/slowproj/slowdash/wiki/Status-and-Updates).

## Docker Images
[DockerHub](https://hub.docker.com/r/slowproj/slowdash)
```
docker pull slowproj/slowdash:2401
```

[GitHub Package](https://github.com/slowproj/slowdash/pkgs/container/slowdash)
```
docker pull ghcr.io/slowproj/slowdash:2401
```

