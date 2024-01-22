FROM python:3.8

COPY . /slowdash

# we install Python packages that might be used by user modules
RUN pip install numpy scipy pandas matplotlib pillow pyyaml psutil psycopg2 mysqlclient influxdb-client redis pymongo couchdb

RUN cd /slowdash/system && make && ln -s /slowdash/bin/slowdash /bin
ENV PYTHONPATH=/slowdash/system/client:$PYTHONPATH

COPY ./ExampleProjects/DummyDataSource /project
WORKDIR /project
VOLUME /project

EXPOSE 80
CMD /bin/slowdash --port=80
