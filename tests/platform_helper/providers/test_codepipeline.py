from unittest.mock import patch

from dbt_platform_helper.providers.codepipeline import CodePipelineProvider


class TestDisableStageTransition:
    @patch(
        "dbt_platform_helper.providers.codepipeline.get_profile_name_from_account_id",
        return_value="myprofilename",
    )
    @patch("dbt_platform_helper.providers.codepipeline.get_aws_session_or_abort")
    def test_expected_calls(
        self,
        mock_get_aws_session_or_abort,
        mock_get_profile_name_from_account_id,
    ):
        provider = CodePipelineProvider()

        provider.disable_stage_transition(
            account_id="111111111111",
            pipeline_name="mypipeline",
            from_stage_name="firststage",
            reason="the reason",
        )

        mock_get_profile_name_from_account_id.assert_called_once_with("111111111111")
        mock_get_aws_session_or_abort.assert_called_once_with("myprofilename")
        mock_session = mock_get_aws_session_or_abort.return_value
        mock_session.client.assert_called_once_with("codepipeline")
        mock_codepipeline_client = mock_session.client.return_value
        mock_codepipeline_client.disable_stage_transition.assert_called_once_with(
            pipelineName="mypipeline",
            stageName="firststage",
            transitionType="Outbound",
            reason="the reason",
        )


class TestEnableStageTransition:
    @patch(
        "dbt_platform_helper.providers.codepipeline.get_profile_name_from_account_id",
        return_value="myprofilename",
    )
    @patch("dbt_platform_helper.providers.codepipeline.get_aws_session_or_abort")
    def test_expected_calls(
        self,
        mock_get_aws_session_or_abort,
        mock_get_profile_name_from_account_id,
    ):
        provider = CodePipelineProvider()

        provider.enable_stage_transition(
            account_id="111111111111", pipeline_name="mypipeline", from_stage_name="firststage"
        )

        mock_get_profile_name_from_account_id.assert_called_once_with("111111111111")
        mock_get_aws_session_or_abort.assert_called_once_with("myprofilename")
        mock_session = mock_get_aws_session_or_abort.return_value
        mock_session.client.assert_called_once_with("codepipeline")
        mock_codepipeline_client = mock_session.client.return_value
        mock_codepipeline_client.enable_stage_transition.assert_called_once_with(
            pipelineName="mypipeline",
            stageName="firststage",
            transitionType="Outbound",
        )
