import datetime

import boto3


def parse_timestamp(string):
    return datetime.datetime.strptime(string, "%Y-%m-%dT%H:%M:%S.%f%z")


class CodePipelineProvider:
    def __init__(self, client: boto3.client):
        self.client = client

    def get_latest_execution_status(self, pipeline_name):
        latest_execution = max(
            self.client.list_pipeline_executions(pipelineName=pipeline_name)[
                "pipelineExecutionSummaries"
            ],
            key=lambda execution: parse_timestamp(execution["startTime"]),
        )
        return latest_execution["status"]
