
# Reverse Proxy with Apache in Docker Compose

## Objectives
Apache container is added to the SlowDash Docker-Compose for:

- URL path (`/slowdash`) instead of a port number (`:18881`)
- Faster HTTP/2 protocol
- Encrypted HTTPS communication between web browsers and the compose
- Password protection with Basic Authentication (with MD5; faster than SlowDash config which uses bcrypt)
- Forwarding HTTP to HTTPS

In this setup, to avoid overhead in using Docker volume mount on every HTTP request, the Apache configuration and credential files are copied in the docker image, rather than using Docker volume mount. Whenever the setting is modified, the container image must be rebuilt (described below).


## Setting up
### Creating SSL/TLS certificate
#### Option 1: Self-signed (for temporary use)
```bash
mkdir -p apache2/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout apache2/ssl/privkey.pem -out apache2/ssl/fullchain.pem -subj "/CN=localhost"
```

or equivalently, use a shell script for the identical command:
```bash
./apache2/generate-selfsigned-certificates.sh
```

This will create certificate files under `apache2/ssl`.

#### Option 2: Let's Encrypt (for long-term setups)
```bash
sudo apt install certbot 
sudo certbot certonly --standalone -d HOSTNAME
```
This will create certificates files under `/etc/letsencrypt/...`. Copy them to `./apache/certs`:
```bash
sudo cp /etc/letsencrypt/live/HOSTNAME/fullchain.pem ./apache2/ssl/
sudo cp /etc/letsencrypt/live/HOSTNAME/privkey.pem ./apache2/ssl/
```


### Creating Basic Authentication file

#### Option 1: Using Apache utils (recommended)
```bash
sudo apt install apache2-utils
htpasswd -bc apache2/htpasswd USERNAME PASSWD
```

or equivalently, use a shell script for the identical command:
```bash
./apache2/generate-htpasswd.sh USERNAME PASSWD
```

This will create the `htpasswd` file under `apache2`.

This uses the MD5 encryption. If you want to use a more secure (and somewhat slower) bcrypt encryption, add option `-B` to the `htpasswd` command. This might affect page loading performance significantly.

#### Option 2: Using SlowDash utils
```bash
PATH/TO/SLOWDASH/utils/slowdash-generate-key.py USERNAME PASSWORD
```

Then copy the value of `key` to `apache2/htpasswd` file.

This uses the bcrypt encryption which is quite CPU-intense. If the response is too slow, use the Apache authentication above, which uses a faster (and less secure) MD5 encryption.


## Running
```bash
docker compose up
```

Then open a browser and connect to `https://localhost/slowdash`.

When password or Apache configuration is changed, run the container with `--build` option:
```bash
docker compose up --build
```
