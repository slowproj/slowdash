---
title: Raspberry-Pi Camera & SlowDash
---

# Ingredient
- Respberry Pi & Camera
- Apache Web Server on Raspberry Pi
- CouchDB for image store
- SlowDash

This uses the `libcamera-still` command, which is included in the standard installation of RPi. A CGI program on RPi takes a photo and returns the image. A SlowDash user module periodically accesses the CGI and stores the image data on CouchDB.

# Setup

Make sure everything is inside a secure network.

## Respberry Pi
### Install Apache2 Web Server
```console
$ sudo apt install apache2
```

### Placing the CGI code
- copy `RPi-PhotoServer/photo.cgi` to your HTML directory
- make it executable
```console
$ chmod 755 photo.cgi
```
- allow camera access
```console
$ sudo adduser www-data video
```
- allow USB-light access
```console
$ sudo adduser www-data dialout
```

### Apache configuration for user CGI
#### Place config files
```console
$ cd /etc/apache2/mods-enabled
$ sudo ln -s ../mods-available/userdir.conf .
$ sudo ln -s ../mods-available/userdir.load .
$ sudo ln -s ../mods-available/cgi.load .
```

#### Edit Files
#### `/etc/apache2/mods-enabled/userdir.conf`
```
AllowOverride: All
```

##### `/home/USER/public_html/.htaccess`
```
  Options +ExecCGI
  AddType application/x-httpd-cgi .cgi
  AddHandler cgi-script .cgi
```

## Server
### Docker-Compose
Nothing is necessary

### Bare-Metal 
#### CouchDB
##### Installation
(Ubuntu 20.04, Jan 17 2024)
```console
$ sudo apt update && sudo apt install -y curl apt-transport-https gnupg
$ curl https://couchdb.apache.org/repo/keys.asc | gpg --dearmor | sudo tee /usr/share/keyrings/couchdb-archive-keyring.gpg >/dev/null 2>&1
$ source /etc/os-release
$ echo "deb [signed-by=/usr/share/keyrings/couchdb-archive-keyring.gpg] https://apache.jfrog.io/artifactory/couchdb-deb/ ${VERSION_CODENAME} main" | sudo tee /etc/apt/sources.list.d/couchdb.list >/dev/null
```

```console
$ sudo apt update
$ sudo apt install -y couchdb
```

##### Configuration
```
http://localhost:5984/_utils/
```

#### Python Module
```console
$ pip3 install couchdb
```


## SlowDash Configuration
### Docker-Compose
- edit `docker-compose.yaml`

### Bare-Metal
- edit `SlowdashProject.yaml`
