from unittest.mock import Mock

from dbt_platform_helper.providers.codepipeline import CodePipelineProvider


class TestGetLastExecutionStatus:
    def test_when_status_is_in_progress(self):
        aws_client = Mock()
        aws_client.list_pipeline_executions.return_value = {
            "pipelineExecutionSummaries": [
                {
                    "status": "InProgress",
                    "startTime": "2026-03-06T19:16:31.030000+00:00",
                },
                {
                    "status": "Succeeded",
                    "startTime": "2026-03-03T12:14:53.743000+00:00",
                },
            ]
        }

        provider = CodePipelineProvider(aws_client)

        result = provider.get_latest_execution_status("my-pipeline")

        assert result == "InProgress"
        aws_client.list_pipeline_executions.assert_called_once_with(pipelineName="my-pipeline")

    def test_when_status_is_success(self):
        aws_client = Mock()
        aws_client.list_pipeline_executions.return_value = {
            "pipelineExecutionSummaries": [
                {
                    "status": "Succeeded",
                    "startTime": "2026-03-06T19:16:31.030000+00:00",
                },
                {
                    "status": "InProgress",
                    "startTime": "2026-03-03T12:14:53.743000+00:00",
                },
            ]
        }

        provider = CodePipelineProvider(aws_client)

        result = provider.get_latest_execution_status("my-pipeline")

        assert result == "Succeeded"
        aws_client.list_pipeline_executions.assert_called_once_with(pipelineName="my-pipeline")

    def test_latest_execution_is_independent_of_list_order(self):
        aws_client = Mock()
        aws_client.list_pipeline_executions.return_value = {
            "pipelineExecutionSummaries": [
                {
                    "status": "Succeeded",
                    "startTime": "2026-03-03T12:14:53.743000+00:00",
                },
                {
                    "status": "InProgress",
                    "startTime": "2026-03-06T19:16:31.030000+00:00",
                },
            ]
        }

        provider = CodePipelineProvider(aws_client)

        result = provider.get_latest_execution_status("my-pipeline")

        assert result == "InProgress"
        aws_client.list_pipeline_executions.assert_called_once_with(pipelineName="my-pipeline")
