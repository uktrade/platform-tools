#!/usr/bin/env bash

TASKS_RUNNING=0

CHECK_COUNT=0
CHECK_NUMBER=5
CHECK_INTERVAL=600

CLIENT_TASK="psql"

while [ $CHECK_COUNT -lt $CHECK_NUMBER ]; do
  sleep $CHECK_INTERVAL
  TASKS_RUNNING="$(ps -e -o pid,comm | grep -c "$CLIENT_TASK")"

  if [[ $TASKS_RUNNING == 0 ]]; then
     CHECK_COUNT=$(( $CHECK_COUNT + 1 ))
     TIME_TO_SHUTDOWN="$(( (CHECK_NUMBER - CHECK_COUNT) * CHECK_INTERVAL ))"
     echo "No clients connected, will shutdown in approximately $TIME_TO_SHUTDOWN seconds"
  else
     CHECK_COUNT=0
     echo "$TASKS_RUNNING clients are connected"
  fi
done

# Trigger CloudFormation stack delete before shutting down
if [[ ! -z $ECS_CONTAINER_METADATA_URI_V4 ]]; then
  aws cloudformation delete-stack --stack-name task-$(curl $ECS_CONTAINER_METADATA_URI_V4 -s | jq -r ".Name")
fi

echo "Shutting down"
