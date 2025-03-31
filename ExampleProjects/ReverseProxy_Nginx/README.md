
# Reverse Proxy with Nginx in Docker Compose

## Objectives
Nginx container is added to the SlowDash Docker-Compose for:

- URL path (`/slowdash`) instead of port number (`:18881`)
- Faster HTTP/2 protocol
- Encrypted HTTPS communication between web browsers and the compose
- Password protection with Basic Authentication
  - by Nginx: currently `.htpasswd` file is volume-mounted, which affects the performance seriously, or
  - by SlowDash config: this is also very slow...


## Setting up
### Creating SSL/TLS certificate
#### Temporary Self-signed
```bash
./generate-certificates.sh
```

This will create certificate files under `nginx/certs`.

#### Let's Encrypt
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot certonly --standalone -d HOSTNAME
```
This will create certificates files under `/etc/letsencrypt/...`. Copy them to `./nginx/certs`:
```bash
sudo cp /etc/letsencrypt/live/HOSTNAME/fullchain.pem ./nginx/certs/
sudo cp /etc/letsencrypt/live/HOSTNAME/privkey.pem ./nginx/certs/
```


### Creating Basic Authentication file
In this example, the password file is volume-mounted into the Nginx container, which affects the performance seriously. SlowDash can be configured (in the `SlowdashProject.yaml` file) to use Basic Authentication, but this is also very slow...

#### Using Apache utils
```bash
$ sudo apt install apache2-utils
$ htpasswd -c nginx/htpasswd USERNAME
```

This will create the `htpasswd` file under `nginx`.

#### Using SlowDash utils
```bash
$ PATH/TO/SLOWDASH/utils/slowdash-generate-key.py USERNAME PASSWORD
```

Then copy the value of `key` to `nginx/htpasswd` file.


## Running
```bash
docker compose up
```

Then open a browser and connect to `https://localhost/slowdash`.

