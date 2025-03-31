# SlowDash + Jupyter behind a Ngynx reverse proxy

## Setting up
see ExampleProjects/ReverseProxy_Ngynx for details

```bash
generate-selfsigned-certificate.sh
htpasswd -bc nginx/htpasswd USERNAME PASSWD
```

## Running
```bash
docker compose up --build
```

Then access to `http://localhost/slowdash`.
