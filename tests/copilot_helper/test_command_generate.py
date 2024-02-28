from unittest.mock import patch

from click.testing import CliRunner

from dbt_copilot_helper.commands.generate import generate as copilot_helper_generate


@patch("dbt_copilot_helper.commands.copilot.make_addons", return_value=None)
@patch("dbt_copilot_helper.commands.pipeline.generate", return_value=None)
def test_pipeline_full_generate_creates_the_pipeline_configuration_and_addons(
    generate, make_addons, fakefs
):
    fakefs.create_dir("copilot")
    CliRunner().invoke(copilot_helper_generate)

    make_addons.assert_called()
    generate.assert_called()
