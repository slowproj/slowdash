# SlowDash + Jupyter/SlowPy behind Nginx, all in Docker Compose

## Ingredients
- SlowDash
- Jupyter with SlowPy
- Nginx reverse proxy for:
  - URL mapping for SlowDash and Jupyter (plus a "home" page)
  - HTTPS encryption
  - Basic authentication
  - HTTP/2 protocol


## Setting up
See ExampleProjects/ReverseProxy/Nginx for details.

```bash
./nginx/generate-selfsigned-certificate.sh
./nginx/generate-htpasswd.sh USERNAME PASSWD
```

## Running
```bash
docker compose up
```

Then access to `http://localhost/`.

## Note
In this example, for simplicity, the credential files as well as the static HTML contents are volume-mounted into the Nginx container, which can slightly affect the performance on every file access (especially on a Windows host). If this becomes a problem, copy these files into the image, as done in the `ExampleProjects/ReverseProxy/Nginx`.
