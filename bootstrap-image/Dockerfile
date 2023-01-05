from nginx:latest

RUN rm /etc/nginx/conf.d/default.conf; mkdir /etc/nginx/templates/
COPY default.conf.template /etc/nginx/templates/
COPY index.html /usr/share/nginx/html/

EXPOSE 8080


