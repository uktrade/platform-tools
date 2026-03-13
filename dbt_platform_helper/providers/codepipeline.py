from datetime import datetime

from dbt_platform_helper.utils.aws import get_aws_session_or_abort
from dbt_platform_helper.utils.aws import get_profile_name_from_account_id


class CodePipelineProvider:
    def get_latest_execution_status(self, account_id, pipeline_name):
        client = self._get_aws_client(account_id)
        execution_list = client.list_pipeline_executions(pipelineName=pipeline_name)
        latest_execution = max(
            execution_list["pipelineExecutionSummaries"],
            key=lambda execution: datetime.fromisoformat(execution["startTime"]),
        )
        return latest_execution["status"]

    def disable_stage_transition(self, account_id, pipeline_name, from_stage_name, reason):
        self._get_aws_client(account_id).disable_stage_transition(
            pipelineName=pipeline_name,
            stageName=from_stage_name,
            transitionType="Outbound",
            reason=reason,
        )

    def enable_stage_transition(self, account_id, pipeline_name, from_stage_name):
        self._get_aws_client(account_id).enable_stage_transition(
            pipelineName=pipeline_name,
            stageName=from_stage_name,
            transitionType="Outbound",
        )

    def _get_aws_client(self, account_id):
        session = get_aws_session_or_abort(get_profile_name_from_account_id(account_id))
        return session.client("codepipeline")
