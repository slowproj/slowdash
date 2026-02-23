# SlowDash Photo Storage (CouchDB)

## CouchDB Setup
### Docker-Compose
Nothing is necessary

### Native (no container)
#### DB Server
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
