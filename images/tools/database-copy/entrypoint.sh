#!/bin/bash

clean_up(){
  echo "Cleaning up dump file"
  rm data_dump.sql
  echo "Removing dump file from S3"
  aws s3 rm s3://${S3_BUCKET_NAME}/data_dump.sql
  if [ ${exit_code} -ne 0 ]
  then
    echo "Aborting data load: Clean up failed"
    exit $exit_code    
  fi
}

handle_errors(){
  exit_code=$1
  message=$2
  if [ ${exit_code} -ne 0 ]
  then
    clean_up
    echo "Aborting data load: {$message}"
    exit $exit_code    
  fi
}

if [ "${DATA_COPY_OPERATION:-DUMP}" != "LOAD" ]
then
  echo "Starting data dump"
  pg_dump --no-owner --no-acl --format c "${DB_CONNECTION_STRING}" > data_dump.sql
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

  echo "Copying data dump from S3"
  aws s3 cp s3://${S3_BUCKET_NAME}/data_dump.sql data_dump.sql
  
  handle_errors $? "Copy failed"

  echo "Scaling down services"
  SERVICES=$(aws ecs list-services --cluster "${ECS_CLUSTER}" | jq -r '.serviceArns[]')
  
  handle_errors $? "Failed to list services"

  for service in ${SERVICES}
  do
    COUNT=$(aws ecs describe-services --cluster "${ECS_CLUSTER}" --services "${service}" | jq '.services[0].desiredCount')
    
    handle_errors $? "Failed to describe service"
    
    SERVICE_NAME=$(basename "${service}")
    CONFIG_FILE="${SERVICE_NAME}.desired_count"
    echo "${COUNT}" > "${CONFIG_FILE}"

    echo ${SERVICE_NAME}
    aws ecs update-service --cluster "${ECS_CLUSTER}" --service "${service}" --desired-count 0 | jq -r '"  Desired Count: \(.service.desiredCount)\n  Running Count: \(.service.runningCount)"'
  
    handle_errors $? "Failed to update service ${SERVICE_NAME}"
  done

  echo "Clearing down the database prior to loading new data"
  psql "${DB_CONNECTION_STRING}" -f /clear_db.sql

  handle_errors $? "Clear down failed"
  
  echo "loading new data from S3"
  pg_restore --format c --dbname "${DB_CONNECTION_STRING}" data_dump.sql
  
  handle_errors $? "Restore failed"
  for service in ${SERVICES}
  do
    CONFIG_FILE="$(basename "${service}").desired_count"
    COUNT=$(cat "${CONFIG_FILE}")
    SERVICE_NAME=$(basename "${service}")
    echo "Scaling up services"
    echo ${SERVICE_NAME}
    aws ecs update-service --cluster "${ECS_CLUSTER}" --service "${service}" --desired-count "${COUNT}" | jq -r '"  Desired Count: \(.service.desiredCount)\n  Running Count: \(.service.runningCount)"'
    handle_errors $? "Failed to update service ${SERVICE_NAME}"
  done

  clean_up

  echo "Stopping data load"
fi
