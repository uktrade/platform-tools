from unittest.mock import Mock
from unittest.mock import call
from unittest.mock import patch

from click.testing import CliRunner

from dbt_platform_helper.commands.generate import generate as platform_helper_generate
from dbt_platform_helper.constants import PLATFORM_HELPER_VERSION_FILE
from dbt_platform_helper.providers.semantic_version import PlatformHelperVersionStatus
from dbt_platform_helper.providers.semantic_version import SemanticVersion


@patch("dbt_platform_helper.commands.copilot.get_aws_session_or_abort")
@patch("dbt_platform_helper.domain.copilot.Copilot.make_addons")
@patch("dbt_platform_helper.domain.pipelines.Pipelines.generate")
def test_platform_helper_generate_creates_the_pipeline_configuration_and_addons(
    mock_pipeline_domain_generate, mock_copilot_domain_make_addons, mock_get_session_or_abort
):
    CliRunner().invoke(platform_helper_generate)

    mock_pipeline_domain_generate.assert_called_once()
    mock_copilot_domain_make_addons.assert_called_once()


@patch("click.secho")
@patch(
    "dbt_platform_helper.domain.versioning.PlatformHelperVersioning._get_version_status",
    new=Mock(
        return_value=PlatformHelperVersionStatus(
            installed=SemanticVersion(1, 0, 1),
            deprecated_version_file=SemanticVersion(1, 0, 0),
        )
    ),
)
@patch("dbt_platform_helper.commands.copilot.get_aws_session_or_abort", new=Mock())
@patch("dbt_platform_helper.domain.copilot.Copilot.make_addons", new=Mock())
@patch("dbt_platform_helper.domain.pipelines.Pipelines.generate", new=Mock())
def test_platform_helper_generate_shows_a_warning_when_version_is_different_than_on_file(
    mock_secho,
    tmp_path,
    no_skipping_version_checks,
):
    CliRunner().invoke(platform_helper_generate)

    mock_secho.assert_has_calls(
        [
            call(
                "Please delete '.platform-helper-version' as it is now deprecated.\nCreate a section in the root of 'platform-config.yml':\n\ndefault_versions:\n  platform-helper: 1.0.0\n",
                fg="magenta",
            ),
            call(
                f"WARNING: You are running platform-helper v1.0.1 against v1.0.0 specified for the project.",
                fg="magenta",
            ),
        ]
    )


@patch(
    "dbt_platform_helper.utils.tool_versioning.get_platform_helper_version_status",
    new=Mock(
        return_value=PlatformHelperVersionStatus(SemanticVersion(1, 0, 0), SemanticVersion(1, 0, 0))
    ),
)
@patch("dbt_platform_helper.commands.copilot.get_aws_session_or_abort", new=Mock())
@patch("dbt_platform_helper.domain.copilot.Copilot.make_addons", new=Mock())
@patch("dbt_platform_helper.domain.pipelines.Pipelines.generate", new=Mock())
def test_platform_helper_generate_does_not_override_version_file_if_exists(
    tmp_path,
):
    contents = "2.0.0"
    version_file_path = tmp_path / PLATFORM_HELPER_VERSION_FILE
    version_file_path.touch()
    version_file_path.write_text(contents)

    assert version_file_path.exists()

    CliRunner().invoke(platform_helper_generate)

    assert version_file_path.exists()
    assert version_file_path.read_text() == contents
