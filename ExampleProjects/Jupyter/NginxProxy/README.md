# SlowDash + Jupyter/SlowPy behind Nginx, all in Docker Compose

## Ingredients
- SlowDash
- Jupyter with SlowPy
- Nginx reverse proxy for:
  - URL mapping for SlowDash and Jupyter
  - Basic authentication
  - HTTPS encryption
  - HTTP/2 protocol


## Setting up
see ExampleProjects/ReverseProxy/Nginx for details

```bash
generate-selfsigned-certificate.sh
htpasswd -bc nginx/htpasswd USERNAME PASSWD
```

## Running
```bash
docker compose up --build
```

Then access to `http://localhost/slowdash`.
