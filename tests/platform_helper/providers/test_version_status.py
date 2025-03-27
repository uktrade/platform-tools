from unittest.mock import Mock

import pytest

from dbt_platform_helper.providers.semantic_version import SemanticVersion
from dbt_platform_helper.providers.version_status import PlatformHelperVersionStatus
from dbt_platform_helper.providers.version_status import VersionStatus


class TestVersionStatus:
    @pytest.mark.parametrize(
        "suite",
        [
            (SemanticVersion(1, 2, 3), SemanticVersion(1, 2, 3), False),
            (SemanticVersion(1, 2, 0), SemanticVersion(1, 2, 3), True),
        ],
    )
    def test_is_outdated(self, suite):
        local_version, latest_release, expected = suite
        assert (
            VersionStatus(installed=local_version, latest=latest_release).is_outdated() == expected
        )

    def test_to_string(self):
        result = f"{VersionStatus(SemanticVersion(1, 2, 0), SemanticVersion(1, 2, 3))}"
        assert result == "VersionStatus: installed: 1.2.0, latest: 1.2.3"


class TestPlatformHelperVersionStatus:
    def test_to_string_with_populated_attributes(self):
        platform_helper_version_status = PlatformHelperVersionStatus(
            SemanticVersion(1, 2, 0),
            SemanticVersion(1, 2, 3),
            SemanticVersion(1, 1, 1),
            SemanticVersion(1, 0, 0),
            SemanticVersion(2, 0, 0),
            {
                "main": SemanticVersion(2, 0, 0),
                "dev": SemanticVersion(2, 1, 1),
            },
        )
        result = f"{platform_helper_version_status}"
        assert (
            result
            == "PlatformHelperVersionStatus: installed: 1.2.0, latest: 1.2.3, deprecated_version_file: 1.1.1, platform_config_default: 1.0.0, cli_override: 2.0.0, pipeline_overrides: main: 2.0.0, dev: 2.1.1"
        )

    def test_to_string_with_no_pipeline_overrides(self):
        platform_helper_version_status = PlatformHelperVersionStatus(
            SemanticVersion(1, 2, 0),
            SemanticVersion(1, 2, 3),
            SemanticVersion(1, 1, 1),
            SemanticVersion(1, 0, 0),
            SemanticVersion(2, 0, 0),
        )
        result = f"{platform_helper_version_status}"
        assert (
            result
            == "PlatformHelperVersionStatus: installed: 1.2.0, latest: 1.2.3, deprecated_version_file: 1.1.1, platform_config_default: 1.0.0, cli_override: 2.0.0"
        )

    @pytest.mark.parametrize(
        "cli_version, config_version, expected",
        [
            ("13.0.0", "12.0.0", "13.0.0"),
            (None, "12.0.0", "12.0.0"),
            ("", "12.0.0", "12.0.0"),
            ("13.0.0", None, "13.0.0"),
            ("13.0.0", "", "13.0.0"),
        ],
    )
    def test_get_required_platform_helper_version_valid_sources(
        self, cli_version, config_version, expected
    ):
        mock_io = Mock()

        result = PlatformHelperVersionStatus(
            cli_override=cli_version, platform_config_default=config_version
        ).get_required_platform_helper_version(mock_io)

        assert result == expected, f"Expected {expected}, but got {result}"

    @pytest.mark.parametrize(
        "cli_version, config_version",
        [
            ("", ""),
            (None, None),
            ("", None),
            (None, ""),
        ],
    )
    def test_get_required_platform_helper_version_when_no_valid_source(
        self, cli_version, config_version
    ):
        mock_io = Mock()

        result = PlatformHelperVersionStatus(
            cli_override=cli_version, platform_config_default=config_version
        ).get_required_platform_helper_version(mock_io)

        mock_io.warn.assert_called_once_with(
            "No platform-helper version specified. No value was provided via CLI, nor was one found in platform-config.yml under `default_versions`."
        )
