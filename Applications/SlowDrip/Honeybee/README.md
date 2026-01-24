# SlowDash with Honeybee

Honeybee: [https://github.com/project8/honeybee](https://github.com/project8/honeybee)


## Building Docker Images
### Honeybee
```
$ git clone https://github.com/project8/honeybee#develop
$ cd honeybee
$ docker build -t honeybee .
$ cd ..
```
(Choose an appropreate branch. Often it is `develop`.)

### SlowDash-Honeybee
```
docker compose build slowdash-honeybee
```
