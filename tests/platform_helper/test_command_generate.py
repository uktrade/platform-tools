from unittest.mock import Mock
from unittest.mock import patch

from click.testing import CliRunner

from dbt_platform_helper.commands.generate import generate as platform_helper_generate


@patch("dbt_platform_helper.commands.generate.click.Context.invoke", return_value=None)
def test_platform_helper_generate_creates_the_pipeline_configuration_and_addons_using_invoke(
    mock_invoke,
):
    CliRunner().invoke(platform_helper_generate)

    assert mock_invoke.called


@patch("dbt_platform_helper.commands.generate.make_addons", return_value=None)
@patch("dbt_platform_helper.commands.generate.pipeline_generate", return_value=None)
def test_platform_helper_generate_creates_the_pipeline_configuration_and_addons(
    mock_generate, mock_make_addons
):
    CliRunner().invoke(platform_helper_generate)

    assert mock_generate.called
    assert mock_make_addons.called


@patch("click.secho")
@patch("dbt_platform_helper.utils.versioning.get_file_app_versions")
@patch(
    "dbt_platform_helper.utils.versioning.running_as_installed_package", new=Mock(return_value=True)
)
@patch("dbt_platform_helper.commands.generate.make_addons", new=Mock(return_value=None))
@patch("dbt_platform_helper.commands.generate.pipeline_generate", new=Mock(return_value=None))
def test_platform_helper_generate_shows_a_warning_when_version_is_different_than_on_file(
    get_file_app_versions, secho
):
    get_file_app_versions.return_value = (1, 0, 1), (1, 0, 0)

    CliRunner().invoke(platform_helper_generate)

    secho.assert_called_once_with(
        f"WARNING: You are running platform-helper v1.0.1 against v1.0.0 specified by .platform-helper-version.",
        fg="red",
    )
