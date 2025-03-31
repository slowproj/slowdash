# SlowDash + Jupyter behind a Nginx reverse proxy

## Setting up
see ExampleProjects/ReverseProxy_Nginx for details

```bash
generate-selfsigned-certificate.sh
htpasswd -bc nginx/htpasswd USERNAME PASSWD
```

## Running
```bash
docker compose up --build
```

Then access to `http://localhost/slowdash`.
