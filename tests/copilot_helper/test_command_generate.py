from unittest import mock

from click.testing import CliRunner

from dbt_copilot_helper.commands.generate import generate as copilot_helper_generate


def test_pipeline_full_generate_creates_the_pipeline_configuration_and_addons(fakefs):
    with mock.patch("dbt_copilot_helper.commands.copilot.make_addons") as mock_make_addons:
        with mock.patch("dbt_copilot_helper.commands.pipeline.generate") as mock_generate:
            CliRunner().invoke(copilot_helper_generate)

            mock_make_addons.assert_called()
            mock_generate.assert_called()
