#!/bin/bash

function run_pipeline() {
    pipeline_type="$1"
    pipeline_name="$2"

    pipeline_type_lowercase=$(echo "$pipeline_type" | tr '[:upper:]' '[:lower:]')

    echo -e "\nTrigger $pipeline_type_lowercase pipeline"
    pipeline_execution_id=$(aws codepipeline start-pipeline-execution --name "$pipeline_name" --profile platform-sandbox | jq -r .pipelineExecutionId)
    echo "$pipeline_type pipeline started with pipeline execution ID: $pipeline_execution_id"

    start=$( date +%s )
    timeout=600

    echo -e "\nWait for $pipeline_type_lowercase pipeline to complete"
    while [ "$pipeline_status" != "Succeeded" ];
    do
      sleep 10
      now=$( date +%s )
      elapsed=$(( now-start ))
      pipeline_status=$(aws codepipeline get-pipeline-execution --pipeline-name "$pipeline_name" --pipeline-execution-id "$pipeline_execution_id" --profile platform-sandbox | jq -r .pipelineExecution.status)
      echo "$pipeline_type pipeline status after $elapsed seconds: $pipeline_status"

      # Todo: Exit early if it's failed

      if [[ elapsed -gt timeout ]]; then
        echo "Error: $pipeline_type pipeline not completed in $timeout seconds"
        exit 1
      fi
    done
}
