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

- Under the project directory, `config` directory is automatically created. Web interface posts files only to this directory.


## Configuration File
Project configuration file describes:

- Name, title of the project
- Data source type and location
- Styles (optional)
- Server-side user modules (optional)
- System control parameters (optional)

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

#### Module Entry (`module`, optional)
- Server-side user Python module. See the [User Module section](UserModule.html) for details.

#### Style Entry (`style`, optional)
See [Styles](#styles) below.

#### System Entry (`system`, optional)
- `file_mode` (default '0644`): Access mode of configuration files uploaded from Web clients
- `file_gid`: Group ID of configuration files uploaded from Web clients

#### Authenticate Entry (`authenticate`, for special purposes)
See [Security Considerations](#security-considerations) below.


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

<strong>WARNING</strong>: Slow-Dash is designed for internal use within a secured network and therefore no security protection is implemented. It is strongly recommended not to expose the system to the public internet. External access is assumed to be done through VPN or ssh tunnel.

## Running in a Docker Container
The SlowDash container image is configured to have a project directory at `/project` and open a port at `18881`. Map the volume and port accordingly:

#### Single Container
```console
$ cd PATH/TO/SLOWDASH/PROJECT
$ docker run -p 18881:18881 -v $(pwd):/project REPO/slowdash:TAG
```

If you built the container image locally, `REPO/slowdash:TAG` will be just `slowdash:TAG` or `slowdash`.

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
If you built the container image locally, `REPO/slowdash:TAG` will be just `slowdash:TAG` or `slowdash`.

```console
$ docker-compose up
```


## Bare-Metal, Running as a User Process
```console
$ slowdash --project-dir=PROJECT_DIR --port=18881
```
- `--project-dir` can be omitted if:
  - `SLOWDASH_PROJECT` environment variable is set, or
  - `slowdash` command is launched at the project directory.
<p>
- The `slowdash` process must keep running while accepting the Web requests. For this, a terminal multiplexer, such as "tumx" or "GNU Screen" would be useful.

## Bare Metal, Launching from CGI
Slowdash can be executed as CGI of a web server such as Apache or Nginx. To setup this, run the script below at the project directory:

```console
$ cd PATH/TO/PROJECT
$ PATH/TO/SLOWDASH/main/server/slowdash-setup-cgi.py
Project: MySlowSystem
Project directory: /home/sanshiro/MySlowSystem/SlowdashProject
Web-file directory: /home/sanshiro/public_html/SlowDash/MySlowSystem
continue? [Y/n] y
CGI directory created: /home/sanshiro/public_html/SlowDash/MySlowSystem

=== INSTALLATION IS SUCCESSFUL ===
- To setup SLOWDASH CGI for another project, set SLOWDASH_PROJECT and run this program.
- It is safe to run this slowdash-setup-cgi.py multiple times, even for the same project.
- CGI can be disabled by deleting the CGI directory.
- Disabled CGI can be re-enabled by running this program again.
- Web-file directory for this project: /home/sanshiro/public_html/SlowDash/MySlowSystem
```

The script will copy all the necessary files under user's web directory (typically `/home/USER/public_html`) and create `.htaccess` with the contents below:
```apache
DirectoryIndex slowhome.html
Options +ExecCGI
AddType application/x-httpd-cgi .cgi
AddHandler cgi-script .cgi
AddType text/javascript .mjs

RewriteEngine On
RewriteRule ^api/(.*)$ slowdash.cgi/$1
```
The web server must be configured so as to:

- enable cgi, userdir and rewrite engine, and 
- allow users to override the parameters used (ExecCGI and FileInfo).

#### Advantages
- As long as the web server is running, there will be no additional maintenance overhead for slow-dash. This is maybe useful to keep data accessible after the measurement has been finished.

#### Disadvantages
- The slowdash command is called on each request, therefore
  - Severe performance overhead exists.
  - No continuous data processing is possible, such as the ones typically done in user modules.

User modules are disabled for CGI by default. To use a module with CGI, set the `cgi_enabled` parameter `true` in the module configuration. Be careful for all the side effects, including performance overhead and security concerns.

# Security Considerations
As already mentioned, <b>SlowDash is designed for internal use only</b> within a secured network and therefore no security protection is implemented. It is strongly recommended not to expose the system to the public internet. External access is assumed to be done <b>through VPN or ssh tunnel</b>.

#### Basic Authentication
In a sad case that you cannot trust your internal friends, the "Basic Authentication" can be used. Combine the authentication <b>with HTTPS using a reverse proxy</b> to encrypt the password and communication.

To use the Basic Authentication, first install the `bcrypt` Python package if it is not yet installed:
```console
$ pip3 install bcrypt
```

Then generate an authentication key by `slowdash authkey/USER?password=PASS`:
```console
$ slowdash authkey/slow?password=dash
{
    "type": "Basic",
    "key": "slow:$2a$12$UWLc20NG5E3drX35cfA/5eFxuDVC0U79dGg4UP/mo55cj222/vuRS"
}
```

Add the key in the project configuration file under the  `authentication` entry:
```yaml
slowdash_project:
  ...

  authentication:
    type: Basic
    key: slow:$2a$12$UWLc20NG5E3drX35cfA/5eFxuDVC0U79dGg4UP/mo55cj222/vuRS
```

This key can also be used for Apache, but some Apache keys, especially old ones such as MD5 keys which are still widely used, can not be used for SlowDash.

#### Only for the CGI mode
Rerun the `slowdash-setup-web.py` command to update the Web Server configuration.
```console
$ PATH/TO/SLOWDASH/main/server/slowdash-setup-cgi.py
Project: MySlowSystem
Project directory: /home/sanshiro/MySlowSystem/SlowdashProject
Web-file directory: /home/sanshiro/public_html/SlowDash/MySlowSystem
User: slow
continue? [Y/n] y
...
```
Note that a new line, `User: slow`, is now added.