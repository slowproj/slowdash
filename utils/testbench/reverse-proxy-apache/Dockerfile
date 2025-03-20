FROM httpd:2.4

COPY slowdash.conf /usr/local/apache2/conf/extra/slowdash.conf
RUN echo "Include conf/extra/slowdash.conf" >> /usr/local/apache2/conf/httpd.conf

COPY ssl/ /etc/apache2/ssl/
