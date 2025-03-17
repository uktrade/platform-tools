import json
import os
from typing import List

import boto3


def update_pipeline_stage_failure(client: boto3.client, pipelines: List[str]):
    for pipeline_name in pipelines:
        print(f"Updating pipeline {pipeline_name}")

        response = client.get_pipeline(name=pipeline_name)
        pipeline = response["pipeline"]

        stage_found = False
        for stage in pipeline["stages"]:
            if "Deploy" in stage["name"]:
                stage["onFailure"] = {"result": "ROLLBACK"}
                stage_found = True

        if not stage_found:
            raise ValueError(f"Stage Deploy not found in pipeline {pipeline_name}")

        client.update_pipeline(pipeline=pipeline)
        print(f"Updated Deploy stage onFailure property for {pipeline_name}")


if __name__ == "__main__":
    pipelines = json.loads(os.environ["PIPELINES"])
    client = boto3.client("codepipeline")
    update_pipeline_stage_failure(client, pipelines)
