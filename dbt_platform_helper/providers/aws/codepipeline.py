import boto3

from dbt_platform_helper.ports.deployed import PipelineDetails
from dbt_platform_helper.ports.deployed import PipelineExecution
from dbt_platform_helper.ports.deployed import PipelinePort
from dbt_platform_helper.ports.deployed import PipelineStatus
from dbt_platform_helper.providers.io import ClickIOProvider


class CodePipeline(PipelinePort):

    def __init__(self, session: boto3.session.Session, io: ClickIOProvider = ClickIOProvider()):
        self.codepipeline_client = session.client("codepipeline")
        self.io = io

    def trigger_deployment(self, details: PipelineDetails):
        variables = [
            {"name": "IMAGE_TAG", "value": details.image_tag},
        ]
        if details.environment:
            variables.append({"name": "ENVIRONMENT", "value": details.environment})
        build_options = {"name": details.name, "variables": variables}
        execution_id = self.codepipeline_client.start_pipeline_execution(**build_options)[
            "pipelineExecutionId"
        ]
        return execution_id

    def get_execution_status(self, pipeline_name: str, execution_id: str):
        try:
            response = self.codepipeline_client.get_pipeline_execution(
                pipelineName=pipeline_name, pipelineExecutionId=execution_id
            )
            status = response["pipelineExecution"]["status"]

            return PipelineExecution(
                execution_id=execution_id, status=PipelineStatus(status), name=pipeline_name
            )
        except Exception as e:
            self.io.warn(f"Failed to get status for {pipeline_name}: {e}")
            return None

    def pipeline_exists(self, pipeline_name):
        try:
            self.codepipeline_client.get_pipeline(name=pipeline_name)
            return True
        except Exception:
            self.io.debug(f"Pipeline {pipeline_name} not found")
        return False

    def get_pipeline_url(self, pipeline_name, execution_id):
        return f"https://eu-west-2.console.aws.amazon.com/codesuite/codepipeline/pipelines/{pipeline_name}/executions/{execution_id}"
