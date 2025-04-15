from unittest.mock import patch

from click.testing import CliRunner

from dbt_platform_helper.commands.generate import generate as platform_helper_generate


@patch("dbt_platform_helper.commands.copilot.get_aws_session_or_abort")
@patch("dbt_platform_helper.domain.copilot.Copilot.make_addons")
@patch("dbt_platform_helper.domain.pipelines.Pipelines.generate")
def test_platform_helper_generate_creates_the_pipeline_configuration_and_addons(
    mock_pipeline_domain_generate, mock_copilot_domain_make_addons, mock_get_session_or_abort
):
    CliRunner().invoke(platform_helper_generate)

    mock_pipeline_domain_generate.assert_called_once()
    mock_copilot_domain_make_addons.assert_called_once()
