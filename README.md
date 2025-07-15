# SlowDash
SlowDash is a web-based platform for monitoring and controlling distributed systems, with a focus on slow controls and data acquisition systems. Originally developed for physics experiments, it provides functionality similar to Grafana but with enhanced control capabilities. Rather than implementing its own data storage, SlowDash integrates with various existing databases, devices, and control systems.

#### Project Goal
- Grafana-like data browser, for time-series data and ROOT-like data objects (graphs, histograms, etc.)
- LabVIEW-like visual control (graphical control panel and control logic behind it)
- Jupyter-like Python scripting

#### Current Status: ~70% of the initial design implemented
- Data browser mostly working
- Controls partly implemented
- Analysis part (scripting etc.) is experimental


## Screenshots
### Interactive Dashboard
<img src="https://slowproj.github.io/slowdash/fig/Gallery-ATDS-Dashboard.png" width="70%">

### Data Visualization
<img src="https://slowproj.github.io/slowdash/fig/Gallery-PlotDemo.png" width="70%">

## Dash-Start
For users with existing time-series data in a database and Docker Compose installed, SlowDash offers immediate visualization capabilities. Visit our ["Dash Start" guide](https://slowproj.github.io/slowdash/#DashStart) for details.

## Setup and Quick Look

### Docker (Linux, Mac, Windows WSL)
<details>

#### Prerequisites
- Git
- Docker and Docker Compose

#### 1. Clone Repository (includes example projects)
```bash
git clone https://github.com/slowproj/slowdash.git
```

#### 2. No Additional Setup Required

#### 3. Launch Example Project
```bash
cd slowdash/ExampleProjects/DummyDataSource
docker compose up
```

#### 4. Access the Interface
Open your web browser and navigate to `http://localhost:18881`

To stop the service:
- Press `Ctrl`-`c` in the terminal, or
- Run `docker compose stop` (or `down` to remove the container)
</details>
  
### Local Docker Image Build
<details>

#### Prerequisites
- Git
- Docker and Docker Compose

#### 1. Clone Repository with Submodules
```bash
git clone https://github.com/slowproj/slowdash.git --recurse-submodules
```

#### 2. Build Image
```bash
cd slowdash
docker build -t slowdash .
```

#### 3. Configure and Launch Example Project
```bash
cd ExampleProjects/DummyDataSource
```
Edit `docker-compose.yaml`: change `image: slowproj/slowdash` to `image: slowdash` to use the local image.
```bash
docker compose up
```

#### 4. Access the Interface
Open your web browser and navigate to `http://localhost:18881`

To stop the service:
- Press `Ctrl`-`c` in the terminal, or
- Run `docker compose stop` (or `down` to remove the container)
</details>


### Native (no container) Installation
<details>
  
#### Prerequisites
- Git
- Python 3.9 or higher

This installation method creates a self-contained environment in the `slowdash` directory, including all Python dependencies in a virtual environment. The installation can be completely removed by deleting this directory.

#### 1. Clone Repository with Submodules
```bash
git clone https://github.com/slowproj/slowdash.git --recurse-submodules
```

#### 2. Setup Environment
```bash
cd slowdash
make
source bin/slowdash-bashrc
```

#### 3. Launch Example Project
```bash
cd ExampleProjects/DummyDataSource
slowdash --port=18881
```

#### 4. Access the Interface
Open your web browser and navigate to `http://localhost:18881`

To stop the service, press `Ctrl`-`c` `in the terminal.

</details>

## Documentation
- Comprehensive documentation is available on our [GitHub Pages](https://slowproj.github.io/slowdash/)
- Additional resources on our GitHub Wiki:
  - [Development Status and Updates](https://github.com/slowproj/slowdash/wiki/Status-and-Updates)
  - [Feature Ideas](https://github.com/slowproj/slowdash/wiki/Feature-Ideas) - Contributions welcome!

## Docker Image Options
#### Build from Source
```bash
git clone https://github.com/slowproj/slowdash.git --recurse-submodules
cd slowdash
docker build -t slowdash .
```

#### Official DockerHub Image
Available at [DockerHub](https://hub.docker.com/r/slowproj/slowdash)
```bash
docker pull slowproj/slowdash
```

#### GitHub Container Registry
Available at [GitHub Packages](https://github.com/slowproj/slowdash/pkgs/container/slowdash)
```bash
docker pull ghcr.io/slowproj/slowdash
```

