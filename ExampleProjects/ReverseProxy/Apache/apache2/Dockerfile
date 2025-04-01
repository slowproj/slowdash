FROM httpd:latest

COPY conf/slowdash.conf /usr/local/apache2/conf/extra/slowdash.conf
RUN echo "Include conf/extra/slowdash.conf" >> /usr/local/apache2/conf/httpd.conf

COPY ssl /usr/local/apache2/conf/ssl
COPY htpasswd /usr/local/apache2/conf/.htpasswd
