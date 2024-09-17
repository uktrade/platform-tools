#!/usr/bin/env bash

set -e

export_file=$(date +%Y-%m-%d-%H.%M.%S).sql

ensure_secrets() {
  if [[ -z "${DESTINATION_S3_URI}" ]]; then
    echo "DESTINATION_S3_URI environment variable not set, exiting"
    exit 1
  fi

  if [[ -z "${DATABASE_CONNECTION_DETAILS}" ]]; then
    echo "DATABASE_CONNECTION_DETAILS environment variable not set, exiting"
    exit 1
  fi
}

export_database() {
  pg_dump "$(echo $DATABASE_CONNECTION_DETAILS | jq -rc '"postgres://\(.username):\(.password)@\(.host):\(.port)/\(.dbname)"')" > $export_file
}

upload_export_to_s3() {
  aws s3 cp $export_file $DESTINATION_S3_URI
}

main() {
  echo "starting export"

  ensure_secrets
  export_database
  upload_export_to_s3

  echo "export completed"
}

main
