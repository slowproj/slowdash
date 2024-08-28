ARG BASE_IMAGE=python:3.12

FROM ${BASE_IMAGE}

RUN apt-get update && apt-get install -y gosu

# we install Python packages that might be used by user modules
RUN pip install numpy scipy pandas matplotlib pillow pyyaml psutil bcrypt requests psycopg2 mysqlclient influxdb-client redis pymongo couchdb


ARG USERNAME=slowuser
ARG GROUPNAME=slowuser
ARG UID=18881
ARG GID=18881
RUN groupadd -g $GID $GROUPNAME && useradd -u $UID -g $GID -d /home/$USERNAME -m -s /bin/bash $USERNAME 

COPY main /slowdash/main
COPY lib /slowdash/lib
COPY docs /slowdash/docs
COPY utils /slowdash/utils
COPY Makefile /slowdash
RUN cd /slowdash && make && ln -s /slowdash/bin/slowdash /bin
RUN pip install /slowdash/lib/slowpy

VOLUME /project
EXPOSE 18881

WORKDIR /project
ENTRYPOINT ["/slowdash/main/docker/entrypoint.sh"]
CMD ["/bin/slowdash", "--port=18881"]
