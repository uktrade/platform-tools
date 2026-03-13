from datetime import datetime
from unittest.mock import patch

import pytest

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
def test_get_in_progress_executions(mock_get_aws_client):
    mock_get_aws_client.return_value.list_pipeline_executions.return_value = {
        "pipelineExecutionSummaries": [
            {
                "pipelineExecutionId": "2977be15-0b81-4c7a-bc07-4c8d935eeb76",
                "status": "InProgress",
            },
            {
                "pipelineExecutionId": "a7510cdf-d49b-4853-971e-7b2fb875a741",
                "status": "Succeeded",
            },
            {
                "pipelineExecutionId": "1bdcce6f-8d60-4f26-bfee-d5cddcc894ab",
                "status": "InProgress",
            },
        ]
    }

    provider = CodePipelineProvider()

    result = provider.get_in_progress_executions(
        account_id="111111111111",
        pipeline_name="mypipeline",
    )

    assert result == [
        {
            "pipelineExecutionId": "2977be15-0b81-4c7a-bc07-4c8d935eeb76",
            "status": "InProgress",
        },
        {
            "pipelineExecutionId": "1bdcce6f-8d60-4f26-bfee-d5cddcc894ab",
            "status": "InProgress",
        },
    ]


@patch("dbt_platform_helper.providers.codepipeline.CodePipelineProvider._get_aws_client")
def test_disable_first_stage_transition(mock_get_aws_client):
    mock_get_aws_client.return_value.get_pipeline.return_value = {
        "pipeline": {"stages": [{"name": "firststage"}]},
    }

    provider = CodePipelineProvider()

    provider.disable_first_stage_transition(
        account_id="111111111111",
        pipeline_name="mypipeline",
        reason="the reason",
    )

    mock_get_aws_client.return_value.get_pipeline.assert_called_once_with(name="mypipeline")
    mock_get_aws_client.return_value.disable_stage_transition.assert_called_once_with(
        pipelineName="mypipeline",
        stageName="firststage",
        transitionType="Outbound",
        reason="the reason",
    )


@patch("dbt_platform_helper.providers.codepipeline.CodePipelineProvider._get_aws_client")
def test_enable_first_stage_transition(mock_get_aws_client):
    mock_get_aws_client.return_value.get_pipeline.return_value = {
        "pipeline": {"stages": [{"name": "firststage"}]},
    }

    provider = CodePipelineProvider()

    provider.enable_first_stage_transition(account_id="111111111111", pipeline_name="mypipeline")

    mock_get_aws_client.return_value.get_pipeline.assert_called_once_with(name="mypipeline")
    mock_get_aws_client.return_value.enable_stage_transition.assert_called_once_with(
        pipelineName="mypipeline",
        stageName="firststage",
        transitionType="Outbound",
    )


@pytest.mark.parametrize("is_enabled", [False, True])
@patch("dbt_platform_helper.providers.codepipeline.CodePipelineProvider._get_aws_client")
def test_is_first_stage_transition_enabled(mock_get_aws_client, is_enabled):
    mock_get_aws_client.return_value.get_pipeline_state.return_value = {
        "stageStates": [
            {
                "stageName": "firststage",
                "inboundTransitionState": {
                    "enabled": True,
                },
            },
            {
                "stageName": "secondstage",
                "inboundTransitionState": {
                    "enabled": is_enabled,
                },
            },
        ],
    }

    provider = CodePipelineProvider()

    result = provider.is_first_stage_transition_enabled(
        account_id="111111111111", pipeline_name="mypipeline"
    )

    assert result == is_enabled
    mock_get_aws_client.return_value.get_pipeline_state.assert_called_once_with(name="mypipeline")


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
