
# Raspberry-Pi Photo Server

## Setup

Make sure everything is inside a secure network.

### Install Apache2 Web Server
```console
$ sudo apt install apache2
```

### Placing the CGI code
- copy `RPi-PhotoServer/photo.cgi` to your HTML directory (e.g., "/home/USER/public_html")
- make it executable
```console
$ chmod 755 photo.cgi
```
(Also make the home and HTML directory accessible by "www-data")
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
AllowOverride: ExecCGI
```

##### `/home/USER/public_html/.htaccess`
```
  Options +ExecCGI
  AddType application/x-httpd-cgi .cgi
  AddHandler cgi-script .cgi
```

### Restart Apache2
```console
$ sudo systemctl restart apache2
```

## Usage

- access to `http://HOST/~USER/photo.cgi` to get a still photo
- access to `http://HOST/~USER/stream.cgi` for live video streaming

Still photos cannot be taken during video streaming.
