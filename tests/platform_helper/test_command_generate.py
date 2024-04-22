from unittest.mock import Mock
from unittest.mock import patch

from click.testing import CliRunner

from dbt_platform_helper.commands.generate import generate as platform_helper_generate
from dbt_platform_helper.utils.versioning import generate_platform_helper_version_file


@patch("dbt_platform_helper.commands.generate.click.Context.invoke", return_value=None)
def test_platform_helper_generate_calls_invoke(
    mock_invoke,
):
    CliRunner().invoke(platform_helper_generate)

    assert mock_invoke.called


def test_platform_helper_generate_creates_the_pipeline_configuration_and_addons():
    with patch(
        "dbt_platform_helper.commands.generate.make_addons", new=Mock(return_value=None)
    ) as mock_make_addons, patch(
        "dbt_platform_helper.commands.generate.pipeline_generate", new=Mock(return_value=None)
    ) as mock_generate:
        # Run the test case
        result = CliRunner().invoke(platform_helper_generate)
        print("RESULT IS >>>>>")
        print(type(result))
        print(result)

        # Check the test result
        assert result.exit_code == 0
        assert mock_generate.call_count == 1
        assert mock_make_addons.call_count == 1


def test_platform_helper_generate_shows_a_warning_when_version_is_different_than_on_file():
    with patch("click.secho") as secho, patch(
        "dbt_platform_helper.utils.versioning.get_file_app_versions"
    ) as get_file_app_versions, patch(
        "dbt_platform_helper.utils.versioning.running_as_installed_package",
        new=Mock(return_value=True),
    ), patch(
        "dbt_platform_helper.commands.generate.make_addons", new=Mock(return_value=None)
    ), patch(
        "dbt_platform_helper.commands.generate.pipeline_generate", new=Mock(return_value=None)
    ):
        get_file_app_versions.return_value = (1, 0, 1), (1, 0, 0)

        CliRunner().invoke(platform_helper_generate)
        print("SECHO IS >>>>>>")
        print(secho)

        secho.assert_called_once_with(
            f"WARNING: You are running platform-helper v1.0.1 against v1.0.0 specified by .platform-helper-version.",
            fg="red",
        )


@patch(
    "dbt_platform_helper.utils.versioning.get_app_versions",
    new=Mock(return_value=[(1, 0, 0), (1, 0, 0)]),
)
@patch("dbt_platform_helper.commands.generate.make_addons", new=Mock(return_value=None))
@patch("dbt_platform_helper.commands.generate.pipeline_generate", new=Mock(return_value=None))
def test_platform_helper_generate_generates_version_file_if_not_exist(tmp_path):
    contents = "1.0.0"
    version_file_path = tmp_path / ".platform-helper-version"

    assert not version_file_path.exists()

    with patch.object(generate_platform_helper_version_file, "__defaults__", (tmp_path,)):
        CliRunner().invoke(platform_helper_generate)

    assert version_file_path.exists()
    assert version_file_path.read_text() == contents


@patch(
    "dbt_platform_helper.utils.versioning.get_app_versions",
    new=Mock(return_value=[(1, 0, 0), (1, 0, 0)]),
)
@patch("dbt_platform_helper.commands.generate.make_addons", new=Mock(return_value=None))
@patch("dbt_platform_helper.commands.generate.pipeline_generate", new=Mock(return_value=None))
def test_platform_helper_generate_does_not_override_version_file_if_exists(tmp_path):
    contents = "2.0.0"
    version_file_path = tmp_path / ".platform-helper-version"
    version_file_path.touch()
    version_file_path.write_text(contents)

    assert version_file_path.exists()

    with patch.object(generate_platform_helper_version_file, "__defaults__", (tmp_path,)):
        CliRunner().invoke(platform_helper_generate)

    assert version_file_path.exists()
    assert version_file_path.read_text() == contents
