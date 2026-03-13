from datetime import datetime
from unittest.mock import patch

from dbt_platform_helper.providers.codepipeline import CodePipelineProvider


class TestGetLatestExecutionStatus:
    @patch("dbt_platform_helper.providers.codepipeline.CodePipelineProvider._get_aws_client")
    def test_when_status_is_in_progress(self, mock_get_aws_client):
        mock_get_aws_client.return_value.list_pipeline_executions.return_value = {
            "pipelineExecutionSummaries": [
                {
                    "status": "InProgress",
                    "startTime": datetime.fromisoformat("2026-03-06T19:16:31.030000+00:00"),
                },
                {
                    "status": "Succeeded",
                    "startTime": datetime.fromisoformat("2026-03-03T12:14:53.743000+00:00"),
                },
            ]
        }

        provider = CodePipelineProvider()

        result = provider.get_latest_execution_status(
            account_id="111111111111",
            pipeline_name="mypipeline",
        )

        assert result == "InProgress"

    @patch("dbt_platform_helper.providers.codepipeline.CodePipelineProvider._get_aws_client")
    def test_when_status_is_succeeded(self, mock_get_aws_client):
        mock_get_aws_client.return_value.list_pipeline_executions.return_value = {
            "pipelineExecutionSummaries": [
                {
                    "status": "Succeeded",
                    "startTime": datetime.fromisoformat("2026-03-06T19:16:31.030000+00:00"),
                },
                {
                    "status": "InProgress",
                    "startTime": datetime.fromisoformat("2026-03-03T12:14:53.743000+00:00"),
                },
            ]
        }

        provider = CodePipelineProvider()

        result = provider.get_latest_execution_status(
            account_id="111111111111",
            pipeline_name="mypipeline",
        )

        assert result == "Succeeded"

    @patch("dbt_platform_helper.providers.codepipeline.CodePipelineProvider._get_aws_client")
    def test_does_not_depend_on_order_executions_are_returned_by_aws(self, mock_get_aws_client):
        mock_get_aws_client.return_value.list_pipeline_executions.return_value = {
            "pipelineExecutionSummaries": [
                {
                    "status": "InProgress",
                    "startTime": datetime.fromisoformat("2026-03-03T12:14:53.743000+00:00"),
                },
                {
                    "status": "Succeeded",
                    "startTime": datetime.fromisoformat("2026-03-06T19:16:31.030000+00:00"),
                },
            ]
        }

        provider = CodePipelineProvider()

        result = provider.get_latest_execution_status(
            account_id="111111111111",
            pipeline_name="mypipeline",
        )

        assert result == "Succeeded"


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
