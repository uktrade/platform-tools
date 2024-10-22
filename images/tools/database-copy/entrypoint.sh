#!/bin/bash

if [ "${DATA_COPY_OPERATION:-DUMP}" != "LOAD" ]
then
  echo "Starting data dump"
  pg_dump --format c "${DB_CONNECTION_STRING}" > data_dump.sql
  exit_code=$?

  if [ ${exit_code} -ne 0 ]
  then
    echo "Aborting data dump"
    exit $exit_code
  fi

  aws s3 cp data_dump.sql s3://${S3_BUCKET_NAME}/
  exit_code=$?

  if [ ${exit_code} -ne 0 ]
  then
    echo "Aborting data dump"
    exit $exit_code
  fi

  echo "Stopping data dump"
else
  echo "Starting data load"

  aws s3 cp s3://${S3_BUCKET_NAME}/data_dump.sql data_dump.sql
  exit_code=$?

  if [ ${exit_code} -ne 0 ]
  then
    echo "Aborting data load"
    exit $exit_code
  fi

  pg_restore --format c --dbname "${DB_CONNECTION_STRING}" data_dump.sql
  exit_code=$?

  if [ ${exit_code} -ne 0 ]
  then
    echo "Aborting data load"
    exit $exit_code
  fi

  echo "Cleaning up dump file"
  rm data_dump.sql
  echo "Removing dump file from S3"
  aws s3 rm s3://${S3_BUCKET_NAME}/data_dump.sql
  echo "Stopping data load"
fi
