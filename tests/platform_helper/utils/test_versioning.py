from pathlib import Path
from typing import Tuple
from typing import Type
from unittest.mock import patch

import pytest
import yaml

from dbt_platform_helper.constants import DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION
from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.providers.semantic_version import (
    IncompatibleMajorVersionException,
)
from dbt_platform_helper.providers.semantic_version import (
    IncompatibleMinorVersionException,
)
from dbt_platform_helper.providers.semantic_version import PlatformHelperVersionStatus
from dbt_platform_helper.providers.semantic_version import SemanticVersion
from dbt_platform_helper.providers.validation import ValidationException
from dbt_platform_helper.utils.versioning import get_aws_versions
from dbt_platform_helper.utils.versioning import get_copilot_versions
from dbt_platform_helper.utils.versioning import (
    get_required_terraform_platform_modules_version,
)
from dbt_platform_helper.utils.versioning import validate_template_version
from tests.platform_helper.conftest import FIXTURES_DIR


# TODO Relocate when we refactor config command in DBTP-1538
class TestConfigCommand:
    @pytest.mark.parametrize(
        "template_check",
        [
            ("addon_newer_major_version.yml", IncompatibleMajorVersionException, ""),
            ("addon_newer_minor_version.yml", IncompatibleMinorVersionException, ""),
            ("addon_older_major_version.yml", IncompatibleMajorVersionException, ""),
            ("addon_older_minor_version.yml", IncompatibleMinorVersionException, ""),
            ("addon_no_version.yml", ValidationException, "Template %s has no version information"),
        ],
    )
    def test_validate_template_version(self, template_check: Tuple[str, Type[BaseException], str]):
        template_name, raises, message = template_check

        with pytest.raises(raises) as exception:
            template_path = str(
                Path(f"{FIXTURES_DIR}/version_validation/{template_name}").resolve()
            )
            validate_template_version(SemanticVersion(10, 10, 10), template_path)

        if message:
            assert (message % template_path) == str(exception.value)

    @patch("subprocess.run")
    @patch(
        "dbt_platform_helper.providers.version.GithubVersionProvider.get_latest_version",
        return_value=SemanticVersion(2, 0, 0),
    )
    def test_get_copilot_versions(self, mock_get_github_released_version, mock_run):
        mock_run.return_value.stdout = b"1.0.0"

        versions = get_copilot_versions()

        assert versions.local == SemanticVersion(1, 0, 0)
        assert versions.latest == SemanticVersion(2, 0, 0)

    @patch("subprocess.run")
    @patch(
        "dbt_platform_helper.providers.version.GithubVersionProvider.get_latest_version",
        return_value=SemanticVersion(2, 0, 0),
    )
    def test_get_aws_versions(self, mock_get_github_released_version, mock_run):
        mock_run.return_value.stdout = b"aws-cli/1.0.0"
        versions = get_aws_versions()

        assert versions.local == SemanticVersion(1, 0, 0)
        assert versions.latest == SemanticVersion(2, 0, 0)


@patch("click.secho")
@patch("dbt_platform_helper.providers.version.version", return_value="0.0.0")
@patch("requests.get")
def test_get_required_platform_helper_version_does_not_call_external_services_if_versions_passed_in(
    mock_get,
    mock_version,
    secho,
):
    required_version = PlatformHelperVersioning()

    result = required_version._resolve_required_version(
        version_status=PlatformHelperVersionStatus(platform_config_default=SemanticVersion(1, 2, 3))
    )

    assert result == "1.2.3"
    mock_version.assert_not_called()
    mock_get.assert_not_called()


@pytest.mark.parametrize(
    "cli_terraform_platform_version, config_terraform_platform_version, expected_version",
    [
        ("feature_branch", "5", "feature_branch"),
        (None, "5", "5"),
        (None, None, DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION),
    ],
)
def test_determine_terraform_platform_modules_version(
    cli_terraform_platform_version, config_terraform_platform_version, expected_version
):
    assert (
        get_required_terraform_platform_modules_version(
            cli_terraform_platform_version, config_terraform_platform_version
        )
        == expected_version
    )


@patch(
    "dbt_platform_helper.providers.version.PyPiVersionProvider.get_latest_version",
    return_value="10.9.9",
)
def test_fall_back_on_default_if_pipeline_option_is_not_a_valid_pipeline(
    mock_latest_release, fakefs
):
    default_version = "1.2.3"
    platform_config = {
        "application": "my-app",
        "default_versions": {"platform-helper": default_version},
        "environments": {"dev": None},
        "environment_pipelines": {
            "main": {
                "versions": {"platform-helper": "1.1.1"},
                "slack_channel": "abc",
                "trigger_on_push": True,
                "environments": {"dev": None},
            }
        },
    }
    fakefs.create_file(Path(PLATFORM_CONFIG_FILE), contents=yaml.dump(platform_config))

    result = PlatformHelperVersioning()._resolve_required_version(
        "bogus_pipeline", version_status=PlatformHelperVersioning().get_version_status()
    )

    assert result == default_version
