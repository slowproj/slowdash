---
title: Project Setup
---

# Configuration

## Project Directory
- Every project has a dedicated project directory. 
- Configuration file is `SlowdashProject.yaml`, placed at the project directory.

- Project directory is specified at run time by one of the followings:
  - `--project-dir` option
  - `SLOWDASH_PROJECT` environmental variable
  - current working directory

- Under the project directory, `config` directory is automatically created. The web interface posts files only to this directory.


## Configuration File
Project configuration file describes:

- Name, title of the project
- Data source type and location
- Control tasks
- Styles
- Server-side user modules
- System control parameters

Example:
```yaml
slowdash_project:
  name: ATDS
  title: Atomic Tritium Demonstrator at UW (ATDS)

  data_source:
    type: PostgreSQL
    parameters:
      url: p8_db_user:****@localhost:5432/p8_sc_db
      time_series:
        schema: data_table[channel]@timestamp=value

  style:
    theme: light
    title:
      color: white
      background: "#4b2e83"

  system:
    file_mode: 0666
```

#### Data Source Entry (`data_source`, often necessary)
- `type`: type of user data store. Common ones are:
  - `PostgreSQL`, `MySQL`, `SQLite`
  - `InfluxDB`
  - `Redis`
  - `MongoDB`
  - `CouchDB`
  - `YAML`
- `parameters`: defined by each data source. See the [Data Binding section](DataBinding.html) for details.

#### TaskEntry (`task`, optional)
- Server-side control tasks (user Python script). See the [Controls section](ControlScript.html) for details.

#### Style Entry (`style`, optional)
See [Styles](#styles) below.

#### System Entry (`system`, optional)
- `file_mode` (default '0644`): Access mode of configuration files uploaded from Web clients
- `file_gid`: Group ID of configuration files uploaded from Web clients
- `our_security_is_perfect`: set `true` to enable Python script uploading; be extremely careful to use this

#### Authenticate Entry (`authenticate`, for special purposes)
See [Security Considerations](#security-considerations) below.

#### Module Entry (`module`, optional)
- Server-side user modules (user Python script). See the [User Module section](UserModule.html) for details.


## Styles
### Configuration
- `theme` (default `light`): currently `light` or `dark`
- `title`:
  - `color`: title text color (default `white`)
  - `background`: title bar background (default `#4b2e83`)
- `logo`: 
  - `file`: file name of the logo image, stored under the project `config` directory.
  - `position`: `left` or `right`
  - `background`: background color (default `none`)
  - `link`: URL to open when the logo is clicked
- `panel`:
  - `plotGridEnabled`, `plotTicksOutwards`: `true` or `false`
  - `plotBackgroundColor`, `plotMarginColor`, `plotFrameColor`, `plotLabelColor`, `plotGridColor`
  - `plotFrameThickness`: default `2`
- `negate`: list of image files used in canvas, the colors of which are to be negated (for dark mode)

### Title-bar Style Example
```yaml
  style:
    title:
      background: linear-gradient(125deg, rgba(75,46,131,1), rgba(75,46,131,1), rgba(75,46,131,0.9))
    logo:
      file: P8_Logo_2017.png
      position: left
      background: linear-gradient(90deg, rgba(255,255,255, 0.6), rgba(255,255,255, 0.4), rgba(255,255,255, 0))
``` 
<img src="fig/ProjectSetup-Styles-TitleBar.png" style="width:50%;margin-left:2em;border:thin solid gray">

The `background` property takes CSS "background" values / expressions. See, e.g., <a href="https://developer.mozilla.org/en-US/docs/Web/CSS/background" target="_blank">a Mozilla document</a> for some examples.

The logo file(s) must be placed under the project `config` directory.

### Plot Style Examples
#### Default Style
<img src="fig/ProjectSetup-Styles-Default.png" style="width:50%;margin-left:2em;border:thin solid gray">

#### Dark Theme
```yaml
  style:
    theme: dark
```
<img src="fig/ProjectSetup-Styles-Dark.png" style="width:50%;margin-left:2em;border:thin solid gray">

#### Custom Style
```yaml
  style:
    panel:
      plotTicksOutwards: true
      plotFrameThickness: 0
      plotBackgroundColor: "#f0f0f0"
      plotGridColor: gray
```
<img src="fig/ProjectSetup-Styles-2.png" style="width:50%;margin-left:2em;border:thin solid gray">


## Testing the Configuration
Running the `slowdash` command without the `--port` option takes parameters from the arguments and prints output to screen. Run the command at the same directory as the configuration file is located.

#### Printing the Configuration
```console
$ slowdash config
{
    "project": {
        "name": "ATDS",
        "title": "Atomic Tritium Demonstrator at UW (ATDS)",
        "error_message": ""
    },
    ...
}
```

#### Printing Channel List
```console
$ slowdash channels
23-03-22 12:48:34 INFO: loaded datasource module "datasource_SQLAlchemy"
[
  {"name": "sccm_Alicat_Inj_Gas"}, 
  {"name": "mbar_CC10_Inj_Gas"}, 
  {"name": "mbar_IG_Vac_MS"}, 
  {"name": "degC_RTD1_Acc_AS"}, 
  {"name": "degC_RTD2_Acc_AS"}, 
  ...
```

#### Printing Data
```console
$ slowdash 'data/sccm_Alicat_Inj_Gas?length=60'
23-03-22 12:50:20 INFO: loaded datasource module "datasource_SQLAlchemy"
{
  "sccm_Alicat_Inj_Gas": {
    "start": 1679514341, "length": 60, 
    "t": [2.364, 12.364, 22.355, 32.366, 42.364, 52.362], 
    "x": [-0.015, -0.014, -0.014, -0.015, -0.014, -0.016]
  }
}
```
When the argument includes a special character of the shell (such as `?` and `&`), quote the entire argument.

# Running the Server

<strong>WARNING</strong>: SlowDash is designed for internal use within a secured network and therefore no security protection is implemented. It is strongly recommended not to expose the system to the public internet. External access is assumed to be done through VPN or ssh tunnel.

## Running in a Docker Container

Docker container images are available on DockerHub and GitHub Container Registry:

- DockerHub ([https://hub.docker.com/r/slowproj/slowdash](https://hub.docker.com/r/slowproj/slowdash)): `slowproj/slowdash:TAG`
- GitHub Package ([https://github.com/slowproj/slowdash/pkgs/container/slowdash](https://github.com/slowproj/slowdash/pkgs/container/slowdash)): `ghcr.io/slowproj/slowdash:TAG`

Or, to build a container locally, run `docker build -t slowdash` at the slowdash source directory:
```console
$ git clone https://github.com/slowproj/slowdash.git --recurse-submodules
$ cd slowdash
$ docker build -t slowdash .
```

The SlowDash container image is configured to have a project directory at `/project` and open a port at `18881`. Map the volume and port accordingly.

#### Single Container
```console
$ cd PATH/TO/SLOWDASH/PROJECT
$ docker run -p 18881:18881 -v $(pwd):/project REPO/slowdash:TAG
```

#### Docker Compose
First write `docker-compose.yaml` at your project directory.
```yaml
version: '3'

services:
  slowdash:
    image: REPO/slowdash:TAG
    volumes:
      - .:/project
    ports:
      - "18881:18881"
```

```console
$ docker compose up
```

## Running as a Bare-Metal User Process
```console
$ slowdash --project-dir=PROJECT_DIR --port=18881
```
- `--project-dir` can be omitted if:
  - `SLOWDASH_PROJECT` environment variable is set, or
  - `slowdash` command is launched at the project directory.
<p>
- The `slowdash` process must keep running while accepting the Web requests. For this, a terminal multiplexer, such as "tumx" or "GNU Screen" would be useful.

## Launching from Apache Web Server (CGI or WSGI)

SlowDash can be executed as a CGI or WSGI module of the Apache web server. 

#### Advantages
- As long as the web server is running, there will be no additional maintenance overhead for this SlowDash project. This is maybe useful to keep the data accessible after the measurement has been finished.

#### Disadvantages
- User Python scripts (control tasks and user modules) are disabled for CGI and WSGI by default, in order to prevent multiple execution of user scripts in an unexpected way. To use a module with CGI/WSGI, set the `enabled_for_cgi` parameter `true` in the module configuration. Be careful for all the side effects, including performance overhead and security concerns.
- CGI starts a SlowDash process for every HTTP request (can be very frequent!), therefore,
  - Severe performance overhead exists, and
  - No continuous data processing is possible, such as the ones typically done in user modules.

WSGI does not have these issues, but be careful for the number of processes that WSGI would launch. If user modules are used, setting the number of WSGI processes to one would be safe. Do not use multi-threading in WSGI processes (set the number of threads to one).

### Prerequisite
- Apache2 Web Server, with cgi and userdir enabled
- Apache module `mod_wsgi` for WSGI

### Setup
There is a setup script in `slowdash/utils`. Run this script at the project directory:
```console
$ cd PATH/TO/PROJECT
$ PATH/TO/SLOWDASH/utils/slowdash-setup-apache.py --interface=CGI   (or --interface=WSGI)
```

#### CGI
To setup CGI, run the script with the `--interface=CGI` option. It will install a set of files under user's public web directory (typically `/home/USER/public_html`), and display messages like:

```console
=== INSTALLATION IS SUCCESSFUL ===
- To setup SLOWDASH CGI for another project, set SLOWDASH_PROJECT and run this program.
- It is safe to run this slowdash-setup-cgi.py multiple times, even for the same project.
- CGI can be disabled by deleting the CGI directory.
- Disabled CGI can be re-enabled by running this program again.
- Web-file directory for this project: /home/sanshiro/public_html/SlowDash/MySlowSystem

=== Apache configuration (CGI) ===
- Install Apache2.
- Enable cgi, userdir, rewrite, and headers modules by:
    $ sudo a2enmod cgid userdir rewrite headers
- Edit /etc/apache2/mods-enabled/userdir.conf to allow overriding.
- Restart Apache by:
    $ sudo systemctl restart apache2
```

CGI requires a proper setting of the Apache web server as shown in the output above. Follow the displayed instructions (modify as needed) if not done previously.

The script places an Apache user directory configuration file (`.htaccess`) with contents like:
```apache
DirectoryIndex slowhome.html
AddType text/javascript .mjs
Options +ExecCGI
AddHandler cgi-script .cgi

RewriteEngine On
RewriteRule ^api/(.*)$ slowdash.cgi/$1
```
For a SlowDash CGI setup in a different way, mind that it requires URL rewriting.

#### WSGI (Daemon)
To setup WSGI, run the script with the `--interface=WSGI` option. It will install a set of files under user's public web directory (typically `/home/USER/public_html`), and display messages like:

```console
=== INSTALLATION IS SUCCESSFUL ===
Public HTML directory for this project is: /home/sanshiro/public_html/SlowDash/MySlowSystem
- To setup a public HTML for another project, set SLOWDASH_PROJECT and run this program.
- It is safe to run this program multiple times, even for the same project.
- Public HTML can be disabled by deleting the HTML directory.
- Disabled public HTML can be re-enabled by running this program again.

=== Apache configuration (WSGI) ===
- Install Apache2.
- Install mod_wsgi by something like:
    $ sudo apt install libapache2-mod-wsgi-py3
    $ sudo yum install mod_wsgi
    $ brew install mod-wsgi
- Enable wsgi, userdir, rewrite, and headers modules by:
    $ sudo a2enmod wsgi userdir rewrite headers
- Add the following lines to /etc/apache2/apache2.conf for WSGI daemon:
    WSGIDaemonProcess slowdash_MySlowSystem_wsgi processes=5 threads=1 home=/home/sanshiro/public_html/SlowDash/MySlowSystem
    WSGIProcessGroup slowdash_MySlowSystem_wsgi
    WSGIApplicationGroup %{GLOBAL}
- Restart Apache by:
    $ sudo systemctl restart apache2
```

WSGI requires a proper setting of the Apache web server as shown in the output above. Follow the displayed instructions (modify as needed) if not done previously.

The script places an Apache user directory configuration file (`.htaccess`) with contents like:
```apache
DirectoryIndex slowhome.html
AddType text/javascript .mjs
Options +ExecCGI
AddHandler wsgi-script .wsgi

RewriteEngine On
RewriteRule ^api/(.*)$ slowdash.wsgi/$1
```
Although dedicated daemon is created for this SlowDash project, currently only one WSGI can be setup on one host. Other SlowDash project must use CGI.


# Security Considerations
As already mentioned, <b>SlowDash is designed for internal use only</b> within a secured network and therefore no security protection is implemented. It is strongly recommended not to expose the system to the public internet. External access is assumed to be done <b>through VPN or ssh tunnel</b>.

#### Basic Authentication
In a case that you cannot trust your internal friends, SlowDash implements the "Basic Authentication". Combine this authentication <b>with HTTPS using a reverse proxy</b> to encrypt the password and communication.

To use the Basic Authentication, first install the `bcrypt` Python package if it is not yet installed:
```console
$ pip3 install bcrypt
```

Then generate an authentication key by the `slowdash-generate-key.py` script in `slowdash/utils`:
```console
$ python3 PATH/TO/SLOWDASH/utils/slowdash-generate-key.py slow dash
{
    "authentication": {
        "type": "Basic",
        "key": "slow:$2a$12$UWLc20NG5E3drX35cfA/5eFxuDVC0U79dGg4UP/mo55cj222/vuRS"
    }
}
```

Here the first argument is the user name and the second is the password.

Add the key in the project configuration file under the  `authentication` entry:
```yaml
slowdash_project:
  ...

  authentication:
    type: Basic
    key: slow:$2a$12$UWLc20NG5E3drX35cfA/5eFxuDVC0U79dGg4UP/mo55cj222/vuRS
```

This key can also be used for Apache, but some Apache keys, especially old ones such as MD5 keys which are still widely used, can not be used for SlowDash.

#### Only for the CGI/WSGI mode
Rerun the `slowdash-setup-apache.py` command to update the Web Server configuration.
```console
$ PATH/TO/SLOWDASH/utils/slowdash-setup-apache.py --interface=CGI   (or --interface=WSGI)
Project: MySlowSystem
Project directory: /home/sanshiro/MySlowSystem/SlowdashProject
Web-file directory: /home/sanshiro/public_html/SlowDash/MySlowSystem
User: slow
continue? [Y/n] y
...
```
Note that a new line, `User: slow`, is now added.


# SlowDash Watchdog (SlowDog)
SlowDog sends HTTP requests to the SlowDash server periodically and if it does not receive a reply before timeout, the dog kills the server and restarts another one.

To enable SlowDog, add `--slowdog` option:
```console
$ slowdash --port=18881 --slowdog
```

SlowDog is enabled in the SlowDash Docker container.
