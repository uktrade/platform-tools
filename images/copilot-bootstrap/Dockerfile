FROM nginx:latest

EXPOSE 8080

COPY default.conf.template /etc/nginx/templates/default.conf.template
COPY index.html /usr/share/nginx/html/index.html
COPY ping.xml /usr/share/nginx/html/pingdom/ping.xml
