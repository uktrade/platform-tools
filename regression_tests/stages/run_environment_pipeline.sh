#!/bin/bash

pipeline_execution_id=$(aws codepipeline start-pipeline-execution --name demodjango-environment-pipeline-TOOLSPR --profile platform-sandbox | jq -r .pipelineExecutionId)
echo "Pipeline started with pipeline execution ID: $pipeline_execution_id"

start=$( date +%s )
timeout=600

while [ "$pipeline_status" != "Succeeded" ];
do
  sleep 10
  now=$( date +%s )
  elapsed=$(( now-start ))
  pipeline_status=$(aws codepipeline get-pipeline-execution --pipeline-name demodjango-environment-pipeline-TOOLSPR --pipeline-execution-id "$pipeline_execution_id" --profile platform-sandbox | jq -r .pipelineExecution.status)
  echo "Pipeline status after $elapsed seconds: $pipeline_status"
  
  if [[ elapsed -gt timeout ]]; then
    echo "Error: Pipeline not completed in $timeout seconds"
    exit 1
  fi
done 