---
title: Installation
---

# Prerequisites
### System Requirements
- UNIX-like Operating System
  - Linux (most extensively tested)
  - macOS and Windows (WSL) are supported
<p>
- Web Browser
  - Firefox most tested, Chrome &amp; Edge &amp; Safari ok, DuckDuckGo &amp; Opera never tested.
  - Also works on mobile devices: tested on iPad

### Docker Installation Requirements
<p>
- Git
- Docker and Docker Compose

### Bare-Metal Installation Requirements
<p>
- Git
- Python 3
  - Version 3.9 or higher
  - Virtual environment (venv) recommended


# Docker Installation
## Using Pre-built Images (Linux, Windows WSL, Mac)

### Initial Setup
No local installation is required. Simply pull a SlowDash image from one of these official repositories:

- DockerHub: [slowproj/slowdash:TAG](https://hub.docker.com/r/slowproj/slowdash/tags)
- GitHub Container Registry: [ghcr.io/slowproj/slowdash:TAG](https://github.com/slowproj/slowdash/pkgs/container/slowdash)

Select either a specific version tag from the repository or use `latest` for the most recent stable release.

### Updating Docker Images
For users of the `:latest` tag from DockerHub or GitHub Container Registry, update to the newest version by removing the local images:
```console
$ docker rmi -f slowproj/slowdash slowproj/slowpy-notebook
```
(Alternative: Use `make remove-docker-images` in the SlowDash directory. You can use tab completion for convenience: `make r[Tab]`.)

Note: This operation removes your current images. Be careful not to lose your working context inside the images. The SlowDash version number is shown in the upper left corner of the home page.


## Building Images Locally
### Initial Setup
```console
$ git clone https://github.com/slowproj/slowdash.git
$ cd slowdash
$ make docker
```

Alternatively, you can execute these commands manually:
```console
$ git clone https://github.com/slowproj/slowdash.git --recurse-submodules
$ cd slowdash
$ docker build -t slowdash .
$ docker build -t slowpy-notebook -f ./lib/slowpy/Dockerfile ./lib/slowpy
```

### Updating Local Images
```console
$ cd PATH/TO/SLOWDASH
$ make update
$ make docker
```

Or execute these commands manually
(Important: Always include `--recurse-submodules` to avoid common integration issues):
```console
$ cd PATH/TO/SLOWDASH
$ git pull --recurse-submodules
$ docker rmi -f slowdash slowpy-notebook
$ docker build -t slowdash .
$ docker build -t slowpy-notebook -f ./lib/slowpy/Dockerfile ./lib/slowpy
```


# Bare-Metal Installation
## Setup
### Using Virtual Environment (Recommended)
This installation method keeps all files contained within the git-cloned directory. You can completely remove the installation by deleting this directory.
```console
$ git clone https://github.com/slowproj/slowdash.git --recurse-submodules
$ cd slowdash
$ make
```

This will create a bash file to set environmental variables. `source` it to include the settings:
```console
$ source PATH/TO/SLOWDASH/bin/slowdash-bashrc
```
The contents of the file look like this:
```bash
export SLOWDASH_DIR=/PATH/TO/SLOWDASH
alias slowdash="$SLOWDASH_DIR/bin/slowdash"
alias slowdash-activate-venv="source $SLOWDASH_DIR/venv/bin/activate"
```
For permanent installation, it might be convenient to include the `source` command in the `.bashrc` (or `.zshrc on Mac) file at your home directory.

### System-wide Installation
```console
$ git clone https://github.com/slowproj/slowdash.git --recurse-submodules
$ cd slowdash
$ make without-venv
$ pip install -r requirements.txt
```
Then activate the environment:
```console
$ source bin/slowdash-bashrc
```

## Verifying Installation
Verify your installation by running:
```console
$ slowdash
Running in venv at /PATH/TO/SLOWDASH/venv
usage: 
  Web-Server Mode:      slowdash.py [Options] --port=PORT
  Command-line Mode:    slowdash.py [Options] COMMAND

Slowdash Version 250128 "Skykomish"

positional arguments:
  COMMAND               API query string. Ex) "config", "channels", "data/CHANNELS?length=LENGTH"

options:
  -h, --help            show this help message and exit
  -p PORT, --port PORT  port number for web connection; command-line mode without this option
  --project-dir PROJECT_DIR
                        project directory (default: current dir if not specified by SLOWDASH_PROJECT environmental variable)
...
```

Test the web interface by starting the server on a test port. You'll see a warning about undefined project settings, which is expected at this stage:
```console
$ slowdash --port=18881
23-05-15 20:12:35 WARNING: unable to find Slowdash Project Dir: specify it with the --project-dir option, set the SLOWDASH_PROJECT environmental variable, or run the slowdash commands at a project directory
listening at port 18881
```
```console
$ firefox http://localhost:18881
```
If successful, you'll see this configuration notice:

<img src="fig/QuickTour-Welcome.png" style="width:40%">

Press `Ctrl`-`c` to stop the server.

## Updating Installation
```console
$ cd PATH/TO/SLOWDASH
$ make update
```

Or manually execute:
```console
$ cd PATH/TO/SLOWDASH
$ git pull --recurse-submodules
$ make
```
Running `make` is always safe, even if no updates are needed.


# Browser Cache Management
After updating the SlowDash server, you may need to clear your browser's cached scripts. To force a cache refresh, hold down the `Shift` key while clicking the reload button on any SlowDash page ("hard refresh": the procedure might be different depending on the browser).
