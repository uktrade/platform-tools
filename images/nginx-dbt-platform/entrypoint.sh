#!/bin/bash

set -euo pipefail

# Proxy pass config.  Pass in $1 path, $2 target (public/private), $3 target_file (public/private).
set_paths() {
    LOCATION_CONFIG="
    location $1 {
      proxy_pass http://$2;
      proxy_set_header Host \$host;
      proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Prefix $1;
      # Experiments from https://stackoverflow.com/questions/75792026/i-am-facing-err-http2-protocol-error-on-my-website...
      gzip on
      proxy_cache off;
      proxy_set_header Upgrade \$http_upgrade;
      proxy_set_header Connection keep-alive;
      proxy_cache_bypass \$http_upgrade;
      proxy_set_header X-Forwarded-Proto \$scheme;
      proxy_redirect off;
      proxy_request_buffering off;
      proxy_buffering off;
    }
"
    echo "$LOCATION_CONFIG" >> $3
}

# Either PRIV_PATH_LIST or PUB_PATH_LIST VARs can be set, not both.
# If neither is set, the default is to make / public
# To enable IP filter set PRIV_PATH_LIST: '/'
if ! [ -z ${PRIV_PATH_LIST+x} ]; then
  PUBLIC_PATHS=""
elif [ -z ${PUB_PATH_LIST+x} ]; then
  set_paths "/" "upstream_server_public" "public_paths.txt"
  PUBLIC_PATHS=$(<public_paths.txt)
else
  set_paths "/" "upstream_server_private" "public_paths.txt"
  for pub in $(echo -e $PUB_PATH_LIST |sed "s/,/ /g")
  do
    set_paths "$pub" "upstream_server_public" "public_paths.txt"
  done
  PUBLIC_PATHS=$(<public_paths.txt)
fi


if (! [ -z ${PRIV_PATH_LIST+x} ] && ! [ -z ${PUB_PATH_LIST+x} ] ) || [ -z ${PRIV_PATH_LIST+x} ]; then
  PRIVATE_PATHS=""
elif [ ${PRIV_PATH_LIST} == '/' ]; then
    set_paths "/" "upstream_server_private" "private_paths.txt"
    PRIVATE_PATHS=$(<private_paths.txt)
else
  set_paths "/" "upstream_server_public" "private_paths.txt"
  for priv in $(echo -e $PRIV_PATH_LIST |sed "s/,/ /g")
  do
    set_paths "$priv" "upstream_server_private" "private_paths.txt"
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
worker_processes auto;
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
    listen 443 ssl http2;
    server_name localhost;

    ssl_certificate /cert.pem;
    ssl_certificate_key /key.pem;
    # By default nginx uses “ssl_protocols TLSv1 TLSv1.1 TLSv1.2 TLSv1.3” and “ssl_ciphers HIGH:!aNULL:!MD5”, so configuring them explicitly is generally not needed.
    # ssl_protocols TLSv1 TLSv1.1 TLSv1.2;


    # Experiments from https://stackoverflow.com/questions/75792026/i-am-facing-err-http2-protocol-error-on-my-website...
    gzip on;
    proxy_max_temp_file_size 0;
    proxy_read_timeout      3600;
    proxy_connect_timeout   300;
    proxy_redirect          off;
    proxy_request_buffering off;
    proxy_buffering off;

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
