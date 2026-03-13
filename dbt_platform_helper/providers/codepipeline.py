from dbt_platform_helper.utils.aws import get_aws_session_or_abort
from dbt_platform_helper.utils.aws import get_profile_name_from_account_id


class CodePipelineProvider:
    def get_in_progress_executions(self, account_id, pipeline_name):
        client = self._get_aws_client(account_id)
        execution_list = client.list_pipeline_executions(pipelineName=pipeline_name)
        return [
            x
            for x in execution_list["pipelineExecutionSummaries"]
            if x["status"] in ("InProgress", "Stopping")
        ]

    def disable_first_stage_transition(self, account_id, pipeline_name, reason):
        client = self._get_aws_client(account_id)
        first_stage_name = client.get_pipeline(name=pipeline_name)["pipeline"]["stages"][0]["name"]
        client.disable_stage_transition(
            pipelineName=pipeline_name,
            stageName=first_stage_name,
            transitionType="Outbound",
            reason=reason,
        )

    def enable_first_stage_transition(self, account_id, pipeline_name):
        client = self._get_aws_client(account_id)
        first_stage_name = client.get_pipeline(name=pipeline_name)["pipeline"]["stages"][0]["name"]
        client.enable_stage_transition(
            pipelineName=pipeline_name,
            stageName=first_stage_name,
            transitionType="Outbound",
        )

    def is_first_stage_transition_enabled(self, account_id, pipeline_name):
        state = self._get_aws_client(account_id).get_pipeline_state(name=pipeline_name)
        return state["stageStates"][1]["inboundTransitionState"]["enabled"]

    def _get_aws_client(self, account_id):
        session = get_aws_session_or_abort(get_profile_name_from_account_id(account_id))
        return session.client("codepipeline")
