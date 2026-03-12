from unittest.mock import patch

from dbt_platform_helper.providers.codepipeline import CodePipelineProvider


@patch("dbt_platform_helper.providers.codepipeline.CodePipelineProvider._get_aws_client")
def test_disable_stage_transition(mock_get_aws_client):
    provider = CodePipelineProvider()

    provider.disable_stage_transition(
        account_id="111111111111",
        pipeline_name="mypipeline",
        from_stage_name="firststage",
        reason="the reason",
    )

    mock_get_aws_client.return_value.disable_stage_transition.assert_called_once_with(
        pipelineName="mypipeline",
        stageName="firststage",
        transitionType="Outbound",
        reason="the reason",
    )


@patch("dbt_platform_helper.providers.codepipeline.CodePipelineProvider._get_aws_client")
def test_enable_stage_transition(mock_get_aws_client):
    provider = CodePipelineProvider()

    provider.enable_stage_transition(
        account_id="111111111111", pipeline_name="mypipeline", from_stage_name="firststage"
    )

    mock_get_aws_client.return_value.enable_stage_transition.assert_called_once_with(
        pipelineName="mypipeline",
        stageName="firststage",
        transitionType="Outbound",
    )


@patch(
    "dbt_platform_helper.providers.codepipeline.get_profile_name_from_account_id",
    return_value="myprofilename",
)
@patch("dbt_platform_helper.providers.codepipeline.get_aws_session_or_abort")
def test_get_aws_client(
    mock_get_aws_session_or_abort,
    mock_get_profile_name_from_account_id,
):
    provider = CodePipelineProvider()

    result = provider._get_aws_client("111111111111")

    mock_get_profile_name_from_account_id.assert_called_once_with("111111111111")
    mock_get_aws_session_or_abort.assert_called_once_with("myprofilename")
    mock_session = mock_get_aws_session_or_abort.return_value
    mock_session.client.assert_called_once_with("codepipeline")
    assert result is mock_session.client.return_value
