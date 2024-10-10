#!/bin/bash

if [ "${DATA_COPY_OPERATION:-DUMP}" != "LOAD" ]
then
  echo "Starting data dump"
  pg_dump --format tar "${DB_CONNECTION_STRING}" | gzip > data_dump.tgz
  aws s3 cp data_dump.tgz s3://${S3_BUCKET_NAME}/
  echo "Stopping data dump"
else
  echo "Starting data restore"
  aws s3 cp s3://${S3_BUCKET_NAME}/data_dump.tgz data_dump.tgz
  ls -al
  gunzip data_dump.tgz
  pg_restore --dbname "${DB_CONNECTION_STRING}" --format tar data_dump.tar
  echo "Stopping data restore"
fi
