FROM python:3.12

# we install Python packages that might be used by user modules
RUN pip install numpy scipy pandas matplotlib pillow pyyaml psutil bcrypt requests psycopg2 mysqlclient influxdb-client redis pymongo couchdb

RUN apt-get update && apt-get install -y gosu


ARG USERNAME=slowuser
ARG GROUPNAME=slowuser
ARG UID=18881
ARG GID=18881
RUN groupadd -g $GID $GROUPNAME && useradd -u $UID -g $GID -d /home/$USERNAME -m -s /bin/bash $USERNAME 

COPY system /slowdash/system
COPY docs /slowdash/docs
COPY utils /slowdash/utils
RUN cd /slowdash/system && make && ln -s /slowdash/bin/slowdash /bin
RUN pip install /slowdash/lib/slowpy

VOLUME /project
EXPOSE 18881

WORKDIR /project
ENTRYPOINT ["/slowdash/system/docker/entrypoint.sh"]
CMD ["/bin/slowdash", "--port=18881"]
