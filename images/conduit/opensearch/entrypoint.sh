#!/usr/bin/env bash

## SETUP Connection Profile
mkdir -p /root/.opensearch-cli/

echo $CONNECTION_SECRET | gawk '{
  match($0, /^https:\/\/([A-Za-z0-9_]+):([^@]+)@(.+)$/, arr);
  print "profiles:"
  print "    - name: connection"
  print "      endpoint: \"https://"arr[3]"\""
  print "      user: \""arr[1]"\""
  print "      password: \""arr[2]"\""
}' > /root/.opensearch-cli/config.yaml

# opensearch-cli requires this specific permission set
chmod 600 /root/.opensearch-cli/config.yaml

## RUN check for connected clients
TASKS_RUNNING=0

CHECK_COUNT=0
CHECK_NUMBER=5
CHECK_INTERVAL=60

while [ $CHECK_COUNT -lt $CHECK_NUMBER ]; do
  sleep $CHECK_INTERVAL

  TASKS_RUNNING="$(ps -e -o pid,comm,args | awk '{if ($4 != "/entrypoint.sh" && $2 == "bash" && $3 == "bash") {print $1}}' | wc -l | xargs)"

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
