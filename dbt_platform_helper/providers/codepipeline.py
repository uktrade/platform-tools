from dbt_platform_helper.utils.aws import get_aws_session_or_abort
from dbt_platform_helper.utils.aws import get_profile_name_from_account_id


class CodePipelineProvider:
    def disable_stage_transition(self, account_id, pipeline_name, from_stage_name, reason):
        session = get_aws_session_or_abort(get_profile_name_from_account_id(account_id))
        codepipeline = session.client("codepipeline")
        codepipeline.disable_stage_transition(
            pipelineName=pipeline_name,
            stageName=from_stage_name,
            transitionType="Outbound",
            reason=reason,
        )

    def enable_stage_transition(self, account_id, pipeline_name, from_stage_name):
        session = get_aws_session_or_abort(get_profile_name_from_account_id(account_id))
        codepipeline = session.client("codepipeline")
        codepipeline.enable_stage_transition(
            pipelineName=pipeline_name,
            stageName=from_stage_name,
            transitionType="Outbound",
        )
