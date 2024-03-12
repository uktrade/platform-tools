from unittest.mock import patch

from click.testing import CliRunner

from dbt_platform_helper.commands.generate import generate as platform_helper_generate


@patch("dbt_platform_helper.commands.generate.make_addons", return_value=None)
@patch("dbt_platform_helper.commands.generate.pipeline_generate", return_value=None)
def test_platform_helper_generate_creates_the_pipeline_configuration_and_addons(
    mock_generate, mock_make_addons
):
    CliRunner().invoke(platform_helper_generate)

    assert mock_generate.called
    assert mock_make_addons.called
