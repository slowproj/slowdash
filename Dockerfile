FROM python:3.8

COPY system /slowdash/system
COPY docs /slowdash/docs
COPY ExampleProjects /slowdash/ExampleProjects

ARG USERNAME=slowuser
ARG GROUPNAME=slowuser
ARG UID=18881
ARG GID=18881
RUN groupadd -g $GID $GROUPNAME && useradd -s /bin/bash -u $UID -g $GID $USERNAME
RUN apt-get update && apt-get install -y gosu

# we install Python packages that might be used by user modules
RUN pip install numpy scipy pandas matplotlib pillow pyyaml psutil bcrypt requests psycopg2 mysqlclient influxdb-client redis pymongo couchdb

RUN cd /slowdash/system && make && ln -s /slowdash/bin/slowdash /bin
RUN pip install /slowdash/system/client/slowpy

WORKDIR /project
VOLUME /project

ENTRYPOINT ["/slowdash/system/docker/entrypoint.sh"]
CMD ["/bin/slowdash", "--port=18881"]
EXPOSE 18881
