from pathlib import Path
from typing import Tuple
from typing import Type
from unittest.mock import patch

import pytest

from dbt_platform_helper.constants import DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION
from dbt_platform_helper.providers.semantic_version import (
    IncompatibleMajorVersionException,
)
from dbt_platform_helper.providers.semantic_version import (
    IncompatibleMinorVersionException,
)
from dbt_platform_helper.providers.semantic_version import SemanticVersion
from dbt_platform_helper.providers.validation import ValidationException
from dbt_platform_helper.utils.tool_versioning import get_aws_versions
from dbt_platform_helper.utils.tool_versioning import get_copilot_versions
from dbt_platform_helper.utils.tool_versioning import (
    get_required_terraform_platform_modules_version,
)
from dbt_platform_helper.utils.tool_versioning import validate_template_version
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
