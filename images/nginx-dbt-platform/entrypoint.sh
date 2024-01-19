#!/bin/bash

set -euo pipefail

# Either PRIV_PATH_LIST or PUB_PATH_LIST VARs can be set, not both.
# If neither is set, the default is to make / public
# To enable IP filter set PRIV_PATH_LIST: '/'
if ! [ -z ${PRIV_PATH_LIST+x} ]; then
  PUBLIC_PATHS=""
elif [ -z ${PUB_PATH_LIST+x} ]; then
  echo -e "    location / {\n\tproxy_pass http://upstream_server_public;\n\tproxy_set_header Host \$host;\n\tproxy_set_header x-forwarded-for \$proxy_add_x_forwarded_for;\n\tproxy_set_header X-Forwarded-Prefix /;\n    }\n" >> public_paths.txt
  PUBLIC_PATHS=$(<public_paths.txt)
else
  echo -e "    location / {\n\tproxy_pass http://upstream_server_private;\n\tproxy_set_header Host \$host;\n\tproxy_set_header x-forwarded-for \$proxy_add_x_forwarded_for;\n\tproxy_set_header X-Forwarded-Prefix /;\n    }\n" >> public_paths.txt
  for pub in $(echo -e $PUB_PATH_LIST |sed "s/,/ /g") 
  do
    echo -e "    location $pub {\n\tproxy_pass http://upstream_server_public;\n\tproxy_set_header Host \$host;\n\tproxy_set_header x-forwarded-for \$proxy_add_x_forwarded_for;\n\tproxy_set_header X-Forwarded-Prefix $pub;\n    }\n" >> public_paths.txt
  done
  PUBLIC_PATHS=$(<public_paths.txt)
fi


if (! [ -z ${PRIV_PATH_LIST+x} ] && ! [ -z ${PUB_PATH_LIST+x} ] ) || [ -z ${PRIV_PATH_LIST+x} ]; then
  PRIVATE_PATHS=""
elif [ ${PRIV_PATH_LIST} == '/' ]; then
    echo -e "    location / {\n\tproxy_pass http://upstream_server_private;\n\tproxy_set_header Host \$host;\n\tproxy_set_header x-forwarded-for \$proxy_add_x_forwarded_for;\n\tproxy_set_header X-Forwarded-Prefix /;\n    }\n" >> private_paths.txt
    PRIVATE_PATHS=$(<private_paths.txt)
else
  echo -e "    location / {\n\tproxy_pass http://upstream_server_public;\n\tproxy_set_header Host \$host;\n\tproxy_set_header x-forwarded-for \$proxy_add_x_forwarded_for;\n\tproxy_set_header X-Forwarded-Prefix /;\n    }\n" >> private_paths.txt
  for priv in $(echo -e $PRIV_PATH_LIST |sed "s/,/ /g") 
  do
    echo -e "    location $priv {\n\tproxy_pass http://upstream_server_private;\n\tproxy_set_header Host \$host;\n\tproxy_set_header x-forwarded-for \$proxy_add_x_forwarded_for;\n\tproxy_set_header X-Forwarded-Prefix $priv;\n    }\n" >> private_paths.txt
  done
  PRIVATE_PATHS=$(<private_paths.txt) 
fi

echo ">> generating self signed cert"
openssl req -x509 -newkey rsa:4086 \
-subj "/C=XX/ST=XXXX/L=XXXX/O=XXXX/CN=localhost" \
-keyout "/key.pem" \
-out "/cert.pem" \
-days 3650 -nodes -sha256

cat <<EOF >/etc/nginx/nginx.conf
user nginx;
worker_processes 2;
events {
  worker_connections 1024;
}

http {
  upstream upstream_server_private{
      server localhost:8000;
  }

  upstream upstream_server_public{
      server localhost:8080;
  }  


  log_format main '\$http_x_forwarded_for - \$remote_user [\$time_local] '
                  '"\$request" \$status \$body_bytes_sent "\$http_referer" '
                  '"\$http_user_agent"' ;

  access_log /var/log/nginx/access.log main;
  error_log /var/log/nginx/error.log;
  server_tokens off;
  server {
    listen 443 ssl;
    server_name localhost;

    ssl_certificate /cert.pem;
    ssl_certificate_key /key.pem;
    ssl_protocols TLSv1 TLSv1.1 TLSv1.2;
    
    include /etc/nginx/mime.types;
    real_ip_header X-Forwarded-For;
    real_ip_recursive on;
    set_real_ip_from 172.16.0.0/20;
    set_real_ip_from 10.0.0.0/8;
    set_real_ip_from 192.168.0.0/16;
    client_max_body_size 600M;

$PUBLIC_PATHS

$PRIVATE_PATHS
  }
}
EOF

echo "Running nginx..."

# Launch nginx in the foreground
/usr/sbin/nginx -g "daemon off;"
