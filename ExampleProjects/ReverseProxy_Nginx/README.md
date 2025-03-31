
# Reverse Proxy with Nginx in Docker Compose

## Setup

### Creating SSL/TLS certificate

#### Temporary Self-signed
```bash
$ ./generate-certificates.sh
```

This will create certificate files under `nginx/certs`.


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


## Run
```bash
docker compose up
```

Then open a browser and connect to `https://localhost/slowdash`.

