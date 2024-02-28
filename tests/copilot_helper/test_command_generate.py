from unittest import mock

from click.testing import CliRunner

from dbt_copilot_helper.commands.generate import generate as copilot_helper_generate


@mock.patch("dbt_copilot_helper.commands.copilot.make_addons", return_value=True)
@mock.patch("dbt_copilot_helper.commands.pipeline.generate", return_value=True)
def test_pipeline_full_generate_creates_the_pipeline_configuration_and_addons(
    generate, make_addons
):
    CliRunner().invoke(copilot_helper_generate)
    generate.assert_called()
    make_addons.assert_called()
