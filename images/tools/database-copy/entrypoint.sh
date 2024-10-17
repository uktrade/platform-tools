#!/bin/bash

if [ "${DATA_COPY_OPERATION:-DUMP}" != "LOAD" ]
then
  echo "Starting data dump"
  pg_dump --format c "${DB_CONNECTION_STRING}" > data_dump.sql
  aws s3 cp data_dump.sql s3://${S3_BUCKET_NAME}/
  echo "Stopping data dump"
else
  echo "Starting data load"
  aws s3 cp s3://${S3_BUCKET_NAME}/data_dump.sql data_dump.sql
  pg_restore --format c --dbname "${DB_CONNECTION_STRING}" data_dump.sql
  echo "Cleaning up dump file"
  rm data_dump.sql
  echo "Removing dump file from S3"
  aws s3 rm s3://${S3_BUCKET_NAME}/data_dump.sql
  echo "Stopping data load"
fi
