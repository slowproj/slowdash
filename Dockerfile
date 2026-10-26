ARG BASE_IMAGE=python:3.13

FROM ${BASE_IMAGE}

RUN apt-get update && apt-get install -y gosu jq libpq-dev

ARG USERNAME=slowuser
ARG GROUPNAME=slowuser
ARG UID=18881
ARG GID=18881
RUN groupadd -g $GID $GROUPNAME && useradd -u $UID -g $GID -d /home/$USERNAME -m -s /bin/bash $USERNAME 

COPY app /slowdash/app
COPY lib /slowdash/lib
COPY bin /slowdash/bin
COPY docs /slowdash/docs
COPY utils /slowdash/utils
COPY Makefile /slowdash
RUN cd /slowdash && make slowdash 
RUN cd /slowdash && pip install -r requirements.txt

VOLUME /project
EXPOSE 18881

WORKDIR /project
ENTRYPOINT ["/slowdash/app/docker/entrypoint.sh"]
CMD ["slowdash", "--port=18881"]
