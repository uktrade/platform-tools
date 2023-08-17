#!/usr/bin/env bash

## SETUP Connection Profile
mkdir -p /usr/share/opensearch/.opensearch-cli/

echo $CONNECTION_SECRET | awk '{
  match($0, /^https:\/\/([A-Za-z0-9_]+):([^@]+)@(.+)$/, arr);
  print "profiles:"
  print "    - name: connection"
  print "      endpoint: https://"arr[3]
  print "      user: "arr[1]
  print "      password: "arr[2]
}' > /usr/share/opensearch/.opensearch-cli/config.yaml

chown opensearch:opensearch /usr/share/opensearch/.opensearch-cli/config.yaml

chmod 600 /usr/share/opensearch/.opensearch-cli/config.yaml


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

echo "Shutting down"
