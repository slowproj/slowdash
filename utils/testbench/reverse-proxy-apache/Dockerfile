FROM httpd:latest

COPY slowdash.conf /usr/local/apache2/conf/extra/slowdash.conf
RUN echo "Include conf/extra/slowdash.conf" >> /usr/local/apache2/conf/httpd.conf
