# SlowDash
SlowDash is a web GUI tool for controlling and monitoring concurrent systems (slow controls and data acquisition), originally designed for physics experiments. Like Grafana, SlowDash does not include data storage systems; it interacts with users and exchanges data and messages with existing databases, devices, and/or other control systems.

#### Project Goal
- Grafana-like data browser, for time-series data and ROOT-like data objects (graphs, histograms, etc.)
- LabVIEW-like visual control (graphical control panel and control logic behind it)
- Jupyter-like Python scripting

#### Current Status: ~70% of the initial design implemented
- Data browser mostly working
- Controls partly implemented
- Analysis part (scripting etc.) is experimental


## Screenshots
### Dashboard
<img src="https://slowproj.github.io/slowdash/fig/Gallery-ATDS-Dashboard.png" width="70%">

### Interactive Plots
<img src="https://slowproj.github.io/slowdash/fig/Gallery-PlotDemo.png" width="70%">

## Dash-Start
If you already have time-series data stored on a database, and have `docker-compose` available on your system, visualization can be done instantly. See the ["Dash Start" section of Github Pages](https://slowproj.github.io/slowdash/#DashStart).

## Setup and Quick Look

### Docker (Linux, Mac, Windows WSL)
<details>

#### Prerequisites for this trial
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
docker compose up
```

#### Step 4: Take a look with a browser
Open a web browser and connect to `http://localhost:18881`.
To stop, type `ctrl`-`c` in the docker-compose window, or use `docker-compose stop` (or `down` to remove the container)
</details>
  
### Building a local Docker Image
<details>

#### Prerequisites for this trial
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
Edit `docker-compose.yaml` to change `image: slowproj/slowdash` to `image: slowdash`
```
docker compose up
```

#### Step 4: Take a look with a browser
Open a web browser and connect to `http://localhost:18881`.
To stop, type `ctrl`-`c` in the docker-compose window, or use `docker-compose stop` (or `down` to remove the container)
</details>


### Bare-Metal
<details>
  
#### Prerequisites for this trial
- Git
- Python3 (>=3.9)

The procedure below will create a new directory, `slowdash`. 
Everything is fully contained under this directory, including Python modules under venv, and nothing in your system will be modified throughout this trial.

#### Step 1: Clone with submodules
```
git clone https://github.com/slowproj/slowdash.git --recurse-submodules
```

#### Step 2: Setup
```
cd slowdash
make
source bin/slowdash-bashrc
```

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
Manuals are on the [Github Pages](https://slowproj.github.io/slowdash/).

See Github Wiki for
- [Status and Updates](https://github.com/slowproj/slowdash/wiki/Status-and-Updates)
- [Feature Ideas](https://github.com/slowproj/slowdash/wiki/Feature-Ideas); your ideas are welcome!

## Docker Images
#### Building from Source
```
git clone https://github.com/slowproj/slowdash.git --recurse-submodules
cd slowdash
docker build -t slowdash .
```

#### DockerHub 
[https://hub.docker.com/r/slowproj/slowdash](https://hub.docker.com/r/slowproj/slowdash)
```
docker pull slowproj/slowdash
```

#### GitHub Package 
[https://github.com/slowproj/slowdash/pkgs/container/slowdash](https://github.com/slowproj/slowdash/pkgs/container/slowdash)
```
docker pull ghcr.io/slowproj/slowdash
```

